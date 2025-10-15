"""
PostgreSQL to OpenSearch ETL Script
Strategy: Full Reload - Extract recruitment data and generate vector embeddings
Features: Batch processing, error handling, execution logging

⚠️ 운영 환경 배포 시 수정 필요:
1. OPENSEARCH_URL: 외부 OpenSearch 클러스터 URL로 변경 (예: http://10.0.0.13:9200)
2. OPENSEARCH_USER/PASSWORD: 보안이 활성화된 경우 인증 정보 추가
3. OS_INDEX: 운영 인덱스명 확인 (기본: candidates)
4. BATCH_SIZE: 데이터 규모에 따라 조정 (기본: 500)
5. INDEX 삭제/재생성 전략: 운영에서는 alias 전환 방식 권장
"""

import os
import sys
import traceback
from datetime import datetime
from typing import List, Dict, Any

import psycopg2
from psycopg2.extras import execute_batch
from opensearchpy import OpenSearch
from opensearchpy.helpers import bulk

# ==================== Environment Variables ====================
# PostgreSQL Connection (Source)
PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# OpenSearch Connection (Target)
# 🔧 PRODUCTION: 외부 OpenSearch URL로 변경 (예: http://10.0.0.13:9200)
OS_URL = os.getenv("OPENSEARCH_URL", "http://opensearch:9200")
OS_INDEX = os.getenv("OS_CAND_INDEX", "candidates")

# 🔧 PRODUCTION: 보안이 활성화된 경우 인증 정보 추가
OS_USER = os.getenv("OPENSEARCH_USER", None)  # 운영: admin 등
OS_PASSWORD = os.getenv("OPENSEARCH_PASSWORD", None)  # 운영: 비밀번호 설정

# Embedding Model Configuration
EMBED_MODEL = os.getenv("EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
EMBED_DIM = int(os.getenv("EMBED_DIM", "384"))

# Constants
DAG_ID = "etl_postgres_to_opensearch_daily"
BATCH_SIZE = 500  # 🔧 PRODUCTION: 대량 데이터의 경우 1000~2000으로 증가 가능
TARGET_SCHEMA = "app"

# Global state
_extraction_data = {
    'rows': [],
    'row_count': 0,
    'run_id': None,
    'started_at': None,
}

# Embedding model cache
_embed_model = None


def get_embedding_model():
    """임베딩 모델 로드 (캐싱)"""
    global _embed_model
    if _embed_model is not None:
        return _embed_model

    try:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {EMBED_MODEL}")
        _embed_model = SentenceTransformer(EMBED_MODEL)
        return _embed_model
    except Exception as e:
        print(f"WARNING: Failed to load embedding model: {str(e)}")
        return None


def generate_embeddings(texts: List[str]) -> List[List[float]]:
    """텍스트 리스트를 임베딩 벡터로 변환"""
    model = get_embedding_model()

    if model:
        import numpy as np
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=True)
        return np.asarray(vecs, dtype="float32").tolist()
    else:
        # Fallback: 랜덤 벡터 (개발/테스트용)
        print("WARNING: Using random embeddings (model not available)")
        import numpy as np
        vecs = []
        for text in texts:
            rng = np.random.default_rng(abs(hash(text)) % (2**32))
            v = rng.standard_normal(EMBED_DIM).astype("float32")
            v /= max(1e-6, np.linalg.norm(v))
            vecs.append(v.tolist())
        return vecs


def get_postgres_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def get_opensearch_client():
    """OpenSearch 클라이언트 생성"""
    # 🔧 PRODUCTION: 보안이 활성화된 경우 http_auth 추가
    if OS_USER and OS_PASSWORD:
        return OpenSearch(
            hosts=[OS_URL],
            http_auth=(OS_USER, OS_PASSWORD),
            use_ssl=True,  # HTTPS 사용 시
            verify_certs=True,  # 인증서 검증 (운영: True 권장)
            timeout=30
        )
    else:
        # Local/Dev 환경 (보안 비활성화)
        return OpenSearch(hosts=[OS_URL], timeout=30)


def log_run_start():
    """ETL 시작 로그 기록"""
    print(f"[{datetime.now()}] Starting ETL run: {DAG_ID}")

    if not all([PG_HOST, PG_USER, PG_PASSWORD, PG_DB, OS_URL]):
        raise ValueError("Required environment variables not set")

    _extraction_data['started_at'] = datetime.now()

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                INSERT INTO {TARGET_SCHEMA}.run_history
                (dag_id, task_id, source_table, target_table, status, started_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING run_id
            """, (
                DAG_ID,
                'log_start',
                f"{TARGET_SCHEMA}.recruitment",
                f"OpenSearch.{OS_INDEX}",
                'IN_PROGRESS',
                _extraction_data['started_at']
            ))
            _extraction_data['run_id'] = cur.fetchone()[0]
            conn.commit()

    print(f"Run ID: {_extraction_data['run_id']}")
    return _extraction_data['run_id']


def extract_from_postgres():
    """PostgreSQL에서 채용 데이터 추출"""
    print(f"[{datetime.now()}] Extracting data from PostgreSQL: {TARGET_SCHEMA}.recruitment")

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # recruitment 테이블에서 전체 데이터 조회
                select_sql = f"""
                    SELECT
                        id,
                        candidate_id,
                        full_name,
                        gender,
                        birth_year,
                        education_level,
                        years_experience,
                        industry,
                        role_title,
                        resume_text,
                        source_updated_at,
                        load_date
                    FROM {TARGET_SCHEMA}.recruitment
                    ORDER BY id
                """

                print(f"Executing: {select_sql}")
                cur.execute(select_sql)
                rows = cur.fetchall()

                _extraction_data['rows'] = rows
                _extraction_data['row_count'] = len(rows)

                print(f"Extracted {len(rows)} rows from PostgreSQL")
                return len(rows)

    except Exception as e:
        log_error('extract_from_postgres', 'EXTRACT', e, f"{TARGET_SCHEMA}.recruitment", None)
        raise


def transform_and_index_to_opensearch():
    """데이터 변환 및 OpenSearch 인덱싱"""
    print(f"[{datetime.now()}] Transforming data and indexing to OpenSearch: {OS_INDEX}")

    rows = _extraction_data['rows']
    if not rows:
        print("No data to index")
        return 0

    try:
        # 1. 임베딩 텍스트 준비 (resume_text 필드 사용)
        print("Preparing text for embeddings...")
        texts = []
        for row in rows:
            resume_text = row[9] or ""  # resume_text (index 9)
            texts.append(resume_text)

        # 2. 임베딩 생성
        print(f"Generating embeddings for {len(texts)} documents...")
        embeddings = generate_embeddings(texts)

        # 3. OpenSearch 문서 준비
        print("Preparing OpenSearch documents...")
        os_client = get_opensearch_client()

        # ⚠️ PRODUCTION WARNING: 인덱스 삭제/재생성 전략
        # 현재: Full Reload (인덱스 삭제 → 재생성 → 데이터 적재)
        # 운영 권장: Blue-Green 배포 (alias 전환)
        #   1. 새 인덱스 생성 (예: candidates_20251006)
        #   2. 데이터 적재
        #   3. alias 'candidates'를 새 인덱스로 전환
        #   4. 이전 인덱스 삭제
        #
        # 🔧 PRODUCTION: 아래 주석 해제하고 alias 로직으로 변경 권장
        # new_index = f"{OS_INDEX}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        if os_client.indices.exists(index=OS_INDEX):
            print(f"Deleting existing index: {OS_INDEX}")
            os_client.indices.delete(index=OS_INDEX)

        # 인덱스 생성 (매핑 포함)
        print(f"Creating index with mapping: {OS_INDEX}")
        index_body = {
            "settings": {
                "index.knn": True,
                # 🔧 PRODUCTION: 샤드/레플리카 수를 클러스터 규모에 맞게 조정
                "number_of_shards": 1,      # 운영: 데이터 크기에 따라 3~5개
                "number_of_replicas": 0     # 운영: 고가용성을 위해 1~2개
            },
            "mappings": {
                "properties": {
                    "candidate_id": {"type": "keyword"},
                    "full_name": {"type": "text"},
                    "gender": {"type": "keyword"},
                    "birth_year": {"type": "integer"},
                    "education_level": {"type": "keyword"},
                    "years_experience": {"type": "integer"},
                    "industry": {"type": "keyword"},
                    "role_title": {"type": "text"},
                    "resume_text": {"type": "text"},
                    "resume_embedding": {
                        "type": "knn_vector",
                        "dimension": EMBED_DIM,
                        "method": {
                            "engine": "lucene",
                            "name": "hnsw",
                            "space_type": "cosinesimil"
                        }
                    },
                    "source_updated_at": {"type": "date"},
                    "load_date": {"type": "date"},
                    "indexed_at": {"type": "date"}
                }
            }
        }
        os_client.indices.create(index=OS_INDEX, body=index_body)

        # 4. Bulk 인덱싱
        print(f"Bulk indexing {len(rows)} documents...")
        actions = []
        for row, embedding in zip(rows, embeddings):
            doc = {
                "_index": OS_INDEX,
                "_id": str(row[0]),  # id를 문서 ID로 사용
                "_source": {
                    "candidate_id": row[1],
                    "full_name": row[2],
                    "gender": row[3],
                    "birth_year": row[4],
                    "education_level": row[5],
                    "years_experience": row[6],
                    "industry": row[7],
                    "role_title": row[8],
                    "resume_text": row[9],
                    "resume_embedding": embedding,
                    "source_updated_at": row[10].isoformat() if row[10] else None,
                    "load_date": row[11].isoformat() if row[11] else None,
                    "indexed_at": datetime.now().isoformat()
                }
            }
            actions.append(doc)

        # Bulk insert
        success, failed = bulk(os_client, actions, chunk_size=BATCH_SIZE, raise_on_error=False)

        print(f"Successfully indexed {success} documents to OpenSearch")
        if failed:
            print(f"WARNING: Failed to index {len(failed)} documents")

        # 5. 인덱스 새로고침
        os_client.indices.refresh(index=OS_INDEX)

        return success

    except Exception as e:
        log_error('transform_and_index', 'LOAD', e, f"{TARGET_SCHEMA}.recruitment", OS_INDEX)
        raise


def log_run_success():
    """ETL 성공 로그 기록"""
    print(f"[{datetime.now()}] Logging ETL success")

    finished_at = datetime.now()
    duration_ms = int((finished_at - _extraction_data['started_at']).total_seconds() * 1000)

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE {TARGET_SCHEMA}.run_history
                SET status = %s,
                    rows_read = %s,
                    rows_written = %s,
                    finished_at = %s,
                    duration_ms = %s,
                    message = %s
                WHERE run_id = %s
            """, (
                'SUCCESS',
                _extraction_data['row_count'],
                _extraction_data['row_count'],
                finished_at,
                duration_ms,
                f"Successfully indexed {_extraction_data['row_count']} documents to OpenSearch",
                _extraction_data['run_id']
            ))
            conn.commit()

    print(f"ETL completed successfully. Duration: {duration_ms}ms")


def log_run_failure():
    """ETL 실패 로그 기록"""
    print(f"[{datetime.now()}] Logging ETL failure")

    finished_at = datetime.now()
    duration_ms = int((finished_at - _extraction_data['started_at']).total_seconds() * 1000)

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    UPDATE {TARGET_SCHEMA}.run_history
                    SET status = %s,
                        finished_at = %s,
                        duration_ms = %s,
                        message = %s
                    WHERE run_id = %s
                """, (
                    'FAILED',
                    finished_at,
                    duration_ms,
                    "ETL pipeline failed - see error_log for details",
                    _extraction_data['run_id']
                ))
                conn.commit()
    except Exception as e:
        print(f"Error logging failure: {str(e)}")


def log_error(task_id: str, step: str, error: Exception, source_table: str, target_table: str):
    """에러 로그 적재"""
    error_message = str(error)
    error_class = type(error).__name__
    stack_trace = traceback.format_exc()

    print(f"ERROR in {task_id}/{step}: {error_message}")
    print(stack_trace)

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"""
                    INSERT INTO {TARGET_SCHEMA}.error_log
                    (run_id, dag_id, task_id, step, error_class, error_message,
                     stacktrace, source_table, target_table, error_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    _extraction_data.get('run_id'),
                    DAG_ID,
                    task_id,
                    step,
                    error_class,
                    error_message[:500],
                    stack_trace[:2000],
                    source_table,
                    target_table,
                    datetime.now()
                ))
                conn.commit()
                print("Error logged to error_log table")
    except Exception as log_error:
        print(f"Failed to log error: {str(log_error)}")


if __name__ == "__main__":
    # 로컬 테스트용
    try:
        log_run_start()
        extract_from_postgres()
        transform_and_index_to_opensearch()
        log_run_success()
        print("ETL completed successfully")
    except Exception as e:
        log_run_failure()
        print(f"ETL failed: {str(e)}")
        sys.exit(1)
