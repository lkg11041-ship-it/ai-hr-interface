import os
import re
from typing import Optional, Dict, Any, List
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException, Query, Body
from opensearchpy import OpenSearch
from services.embedder import embed_query

router = APIRouter()
os_client = OpenSearch(hosts=[os.getenv("OPENSEARCH_URL","http://localhost:9200")])

def get_pg_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=os.getenv("POSTGRES_PORT", "5432"),
        database=os.getenv("POSTGRES_DB", "recruit"),
        user=os.getenv("POSTGRES_USER", "app"),
        password=os.getenv("POSTGRES_PASSWORD", "app_pw"),
        cursor_factory=RealDictCursor
    )

def parse_experience_years(q: str) -> Dict[str, int]:
    """경력 조건만 파싱"""
    filters = {}

    # "N년 이상", "N년 초과"
    match = re.search(r'(\d+)\s*년\s*(이상|초과)', q)
    if match:
        filters['min_years'] = int(match.group(1))
        if match.group(2) == '초과':
            filters['min_years'] += 1

    # "N년 미만", "N년 이하"
    match = re.search(r'(\d+)\s*년\s*(미만|이하)', q)
    if match:
        filters['max_years'] = int(match.group(1))
        if match.group(2) == '미만':
            filters['max_years'] -= 1

    # "N~M년", "N-M년"
    match = re.search(r'(\d+)\s*[-~]\s*(\d+)\s*년', q)
    if match:
        filters['min_years'] = int(match.group(1))
        filters['max_years'] = int(match.group(2))

    return filters

@router.get("/hybrid")
def hybrid(
    q: Optional[str] = Query(None),
    index: str = "candidates",
    min_years: Optional[int] = Query(None),
    max_years: Optional[int] = Query(None),
    min_age: Optional[int] = Query(None),
    max_age: Optional[int] = Query(None),
    gender: Optional[str] = Query(None)
):
    """
    하이브리드 검색:
    1. PostgreSQL: 구조화된 데이터 필터링 (경력, 나이, 성별 등)
    2. OpenSearch: 벡터 유사도 검색 (성격, 성향, 경험 등 자연어)
    """
    try:
        # === Step 1: PostgreSQL에서 구조화된 필터 적용 ===
        experience_filters = parse_experience_years(q) if q else {}
        if min_years is not None:
            experience_filters['min_years'] = min_years
        if max_years is not None:
            experience_filters['max_years'] = max_years

        # PostgreSQL 쿼리 빌드
        pg_where_clauses = []
        pg_params = []

        if 'min_years' in experience_filters:
            pg_where_clauses.append("experience_years >= %s")
            pg_params.append(experience_filters['min_years'])

        if 'max_years' in experience_filters:
            pg_where_clauses.append("experience_years <= %s")
            pg_params.append(experience_filters['max_years'])

        if min_age is not None:
            pg_where_clauses.append("age >= %s")
            pg_params.append(min_age)

        if max_age is not None:
            pg_where_clauses.append("age <= %s")
            pg_params.append(max_age)

        if gender:
            pg_where_clauses.append("gender = %s")
            pg_params.append(gender)

        # PostgreSQL에서 후보자 필터링
        pg_conn = get_pg_connection()
        pg_cursor = pg_conn.cursor()

        if pg_where_clauses:
            where_sql = " WHERE " + " AND ".join(pg_where_clauses)
        else:
            where_sql = ""

        pg_cursor.execute(f"""
            SELECT applicant_id, name, age, gender, education, experience_years, skills, industries
            FROM candidates
            {where_sql}
        """, pg_params)

        candidates = pg_cursor.fetchall()
        pg_cursor.close()
        pg_conn.close()

        if not candidates:
            return {"hits": {"total": {"value": 0}, "hits": []}}

        # 필터링된 후보자 ID 목록
        candidate_ids = [c['applicant_id'] for c in candidates]

        # === Step 2: OpenSearch 벡터 유사도 검색 ===
        # 경력 필터 텍스트 제거
        clean_query = ""
        if q:
            clean_query = re.sub(r'\d+\s*[-~]\s*\d+\s*년', '', q)
            clean_query = re.sub(r'\d+\s*년\s*(이상|초과|미만|이하)', '', clean_query)
            clean_query = re.sub(r'(경력|추천|찾아|검색|해줘|사람|해주|세요|주세요|나이|성별|남자|여자)', '', clean_query)
            clean_query = clean_query.strip()

        # === Step 2: OpenSearch 검색 쿼리 구성 ===
        os_body = {
            "size": 20,
            "_source": ["applicant_id", "passage_text"],
            "highlight": {
                "fields": {
                    "passage_text": {
                        "fragment_size": 200,
                        "number_of_fragments": 3
                    }
                },
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }
        }

        # 자연어 쿼리가 있으면 텍스트 검색 (벡터는 향후 추가)
        if clean_query and len(clean_query) >= 2:
            # 텍스트 검색 쿼리
            os_body["query"] = {
                "bool": {
                    "must": [
                        {"terms": {"applicant_id": candidate_ids}}
                    ],
                    "should": [
                        {"match": {"passage_text": {"query": clean_query, "boost": 3.0, "fuzziness": "AUTO"}}},
                        {"match_phrase": {"passage_text": {"query": clean_query, "boost": 5.0, "slop": 2}}}
                    ]
                }
            }
        else:
            # 필터만 있는 경우 - ID 매칭
            os_body["query"] = {
                "terms": {"applicant_id": candidate_ids}
            }

        os_resp = os_client.search(index=index, body=os_body)

        # === Step 3: PostgreSQL 데이터 + OpenSearch 결과 결합 ===
        # PostgreSQL 데이터를 dict로 변환
        candidates_dict = {c['applicant_id']: dict(c) for c in candidates}

        # OpenSearch 결과에 PostgreSQL 데이터 병합
        merged_hits = []
        for hit in os_resp['hits']['hits']:
            applicant_id = hit['_source']['applicant_id']
            if applicant_id in candidates_dict:
                merged_source = candidates_dict[applicant_id].copy()
                merged_source['passage_text'] = hit['_source'].get('passage_text', '')

                merged_hits.append({
                    "_id": hit['_id'],
                    "_score": hit['_score'],
                    "_source": merged_source,
                    "highlight": hit.get('highlight', {})
                })

        return {
            "took": os_resp.get('took', 0),
            "hits": {
                "total": {"value": len(merged_hits)},
                "hits": merged_hits
            }
        }

    except Exception as e:
        raise HTTPException(500, str(e))

@router.post("/index/candidate")
def index_candidate(index: str = "candidates", doc: dict = Body(...)):
    try:
        v = embed_query(doc.get("passage_text",""))
        doc["passage_embedding"] = v
        res = os_client.index(index=index, body=doc)
        return {"indexed": True, "id": res.get("_id")}
    except Exception as e:
        raise HTTPException(500, str(e))
