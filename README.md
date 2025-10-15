# Recruit AI Starter (Dual-mode: Local OpenAPI ↔ Prod LLaMA, OpenSearch + Postgres + Airflow + React/TS)

- **Local**: OpenAI 호환 **Open API** 사용(내 GPU 불필요), compose 내 Postgres/OpenSearch 컨테이너.
- **Prod**: 자체 호스팅 **LLaMA(vLLM/TGI)** + **외부 Postgres/OpenSearch/Oracle**(IP 연결).

## 빠른 시작

### Local (Open API)
```bash
cp .env.local .env
docker compose up -d --build
docker compose exec backend python scripts/bootstrap_search.py
```
- Airflow: http://localhost:8081  (airflow/airflow)
- Backend: http://localhost:8000/docs
- Frontend: http://localhost:5173

### Prod (LLaMA + 외부 DB/Search)
```bash
cp .env.prod.example .env
# .env의 IP/계정/모델명을 실제 값으로 수정
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```
- Airflow DAG 자동 실행 순서:
  - `02:30` **etl_oracle_to_postgres_recruit_daily**: Oracle → Postgres 추출/적재 (Full Reload)
  - `04:00` **etl_postgres_to_opensearch_daily**: Postgres → OpenSearch 벡터 인덱싱 (임베딩 생성)
- 실패 시 자동 에러 로깅 및 추적

## 폴더 개요
- `infra/opensearch/` : 하이브리드 파이프라인(RRF/정규화), 후보 인덱스 매핑
- `infra/llm/` : vLLM/TGI Docker/K8s 템플릿
- `airflow/` : Dockerfile + DAGs(Oracle ETL, 벡터 인덱싱) + ETL 스크립트
- `db/` : 초기 스키마(SQL) — hr 스키마
- `backend/` : FastAPI(LLM 라우팅, OpenSearch 하이브리드 API, 관리 엔드포인트)
- `frontend/` : React + Vite + TypeScript(결과 카드/하이라이트)

## 운영 배포
- **일반 환경**: [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md)
- **폐쇄망 환경**: [OFFLINE_DEPLOYMENT.md](OFFLINE_DEPLOYMENT.md)

## LLaMA 전환
- vLLM/TGI 템플릿은 `infra/llm/`에 있음. 기동 후 `.env`의 `LLM*_URL`을 해당 IP:PORT로 지정.
