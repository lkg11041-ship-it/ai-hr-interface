# Recruit AI Starter - 프로젝트 상태

## 현재 아키텍처 (Hybrid Search)

### 데이터 저장 구조
1. **PostgreSQL (구조화된 데이터)**
   - 테이블: `candidates`
   - 저장 항목: applicant_id, name, age, gender, education, experience_years, skills[], industries[]
   - 용도: 경력, 나이, 성별 등 정형 데이터 필터링

2. **OpenSearch (비구조화된 데이터)**
   - 인덱스: `candidates`
   - 저장 항목: applicant_id, passage_text, passage_embedding (vector)
   - 용도: 자기소개서 자연어 검색, 성격/성향 벡터 유사도 검색

### 검색 로직 (Hybrid Search)
```
/search/hybrid?q=<query>&min_years=<int>&max_years=<int>&min_age=<int>&max_age=<int>&gender=<str>
```

**처리 순서:**
1. PostgreSQL에서 구조화된 필터 적용 (경력, 나이, 성별)
2. 필터링된 candidate_ids를 가져옴
3. OpenSearch에서 벡터 유사도 + 텍스트 검색 (passage_text, passage_embedding)
4. PostgreSQL 데이터 + OpenSearch 검색 결과 병합하여 반환

## 최근 작업 내용

### 2025-10-01 작업
1. ✅ PostgreSQL에 `candidates` 테이블 생성
2. ✅ OpenSearch에서 PostgreSQL로 구조화된 데이터 마이그레이션 (20명)
3. ✅ `backend/routers/search.py` 하이브리드 검색 구현
4. ⏸️ 테스트 중단됨 (사용자 요청으로 중단)

### 주요 파일

#### `backend/routers/search.py`
- PostgreSQL + OpenSearch 하이브리드 검색
- 구조화된 필터: 경력, 나이, 성별
- 벡터 검색: 자기소개서 내용 기반 유사도

#### `scripts/migrate_to_postgres.py`
- OpenSearch → PostgreSQL 마이그레이션 스크립트
- 20명 후보자 데이터 이관 완료

#### `db/init/01_create_tables.sql`
- PostgreSQL candidates 테이블 스키마
- 인덱스: experience_years, age, gender, skills (GIN), industries (GIN)

## 서비스 기동 방법

```bash
# 전체 서비스 시작
docker compose up -d

# 백엔드만 재시작
docker compose restart backend

# PostgreSQL 확인
docker compose exec postgres psql -U app -d recruit -c "SELECT COUNT(*) FROM candidates;"

# OpenSearch 확인
curl "http://localhost:9200/candidates/_count" -u admin:MyStrongP@ssw0rd123! -k
```

## 환경 변수 (.env)
```
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=recruit
POSTGRES_USER=app
POSTGRES_PASSWORD=app_pw

OPENSEARCH_URL=http://opensearch:9200
OPENSEARCH_INITIAL_ADMIN_PASSWORD=MyStrongP@ssw0rd123!
```

## 테스트 쿼리 예시

### 구조화된 필터만
```bash
curl "http://localhost:8000/search/hybrid?q=경력 10년 미만"
# → PostgreSQL에서 experience_years < 10 필터링
```

### 자연어 검색
```bash
curl "http://localhost:8000/search/hybrid?q=데이터 분석 경험"
# → OpenSearch 벡터 유사도 + 텍스트 검색
```

### 하이브리드 (구조화 + 자연어)
```bash
curl "http://localhost:8000/search/hybrid?q=팀워크&min_years=5"
# → PostgreSQL: 경력 5년 이상 필터
# → OpenSearch: "팀워크" 벡터 유사도 검색
```

## 다음 작업 (TODO)
- [ ] 하이브리드 검색 테스트 완료
- [ ] 프론트엔드에서 새로운 필터 파라미터 지원 (age, gender)
- [ ] Airflow DAG에서 데이터 동기화 (PostgreSQL ↔ OpenSearch)

## 문제 해결

### 백엔드 로그 확인
```bash
docker compose logs --tail=50 backend
```

### PostgreSQL 테이블 확인
```bash
docker compose exec postgres psql -U app -d recruit -c "\d candidates"
```

### OpenSearch 매핑 확인
```bash
curl "http://localhost:9200/candidates/_mapping" -u admin:MyStrongP@ssw0rd123! -k
```
