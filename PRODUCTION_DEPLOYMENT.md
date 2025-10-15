# 운영 환경 배포 가이드

이 문서는 Recruit AI Starter 프로젝트를 우분투 서버에 운영 배포하는 전체 과정을 설명합니다.

## 📋 목차

1. [시스템 아키텍처](#시스템-아키텍처)
2. [사전 준비](#사전-준비)
3. [서버 환경 설정](#서버-환경-설정)
4. [PostgreSQL 설정](#postgresql-설정)
5. [OpenSearch 설정](#opensearch-설정)
6. [Airflow 배포](#airflow-배포)
7. [Backend/Frontend 배포](#backendfrontend-배포)
8. [배포 후 검증](#배포-후-검증)
9. [운영 관리](#운영-관리)
10. [트러블슈팅](#트러블슈팅)

---

## 시스템 아키텍처

### 데이터 파이프라인

```
┌──────────────┐
│  Oracle DB   │  (소스)
│  HR.RECRUIT  │
└──────┬───────┘
       │ 02:30 (매일)
       ▼
┌─────────────────────────┐
│   Airflow Scheduler     │
│  ETL Oracle→PostgreSQL  │
└──────┬──────────────────┘
       │
       ▼
┌──────────────┐
│ PostgreSQL   │  (데이터 저장소)
│ app.recruit  │
└──────┬───────┘
       │ 04:00 (매일)
       ▼
┌─────────────────────────┐
│   Airflow Scheduler     │
│  벡터 임베딩 생성       │
└──────┬──────────────────┘
       │
       ▼
┌──────────────┐
│  OpenSearch  │  (벡터 DB + 검색)
│  candidates  │
└──────┬───────┘
       │
       ▼
┌─────────────────────────┐
│  Backend (FastAPI)      │
│  + Frontend (React)     │
└─────────────────────────┘
```

### 필수 서버 및 포트

| 서버 | 역할 | 포트 |
|------|------|------|
| Oracle | 소스 데이터 | 1521 |
| PostgreSQL | 데이터 저장소 | 5432 |
| OpenSearch | 벡터 검색 | 9200 |
| Airflow | ETL 오케스트레이션 | 8081 |
| Backend | API 서버 | 8000 |
| Frontend | 웹 UI | 5173 |

---

## 사전 준비

### 1. 필수 접속 정보 확인

#### Oracle (소스)
- [ ] 호스트 IP (예: 10.0.0.21)
- [ ] 포트 (기본: 1521)
- [ ] 서비스명 (예: ORCLPDB1)
- [ ] 사용자명 (예: hr)
- [ ] 비밀번호

#### PostgreSQL (타겟)
- [ ] 호스트 IP (예: 10.0.0.11)
- [ ] 포트 (기본: 5432)
- [ ] 데이터베이스명 (예: recruit)
- [ ] 사용자명 (예: recruit_app)
- [ ] 비밀번호

#### OpenSearch (검색)
- [ ] 호스트 IP (예: 10.0.0.12)
- [ ] 포트 (기본: 9200)
- [ ] 인증 정보 (보안 활성화 시)

### 2. 네트워크 요구사항

```bash
# Airflow 서버 → Oracle
telnet 10.0.0.21 1521

# Airflow 서버 → PostgreSQL
telnet 10.0.0.11 5432

# Airflow 서버 → OpenSearch
curl http://10.0.0.12:9200
```

---

## 서버 환경 설정

### 1. 우분투 서버 업데이트

```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Docker 설치

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
newgrp docker

# Docker Compose 플러그인 설치
sudo apt install docker-compose-plugin -y

# 버전 확인
docker --version
docker compose version
```

### 3. 프로젝트 배포

```bash
# 프로젝트 디렉토리로 이동
cd /opt
sudo git clone <your-repo-url> recruit-ai
sudo chown -R $USER:$USER recruit-ai
cd recruit-ai

# 또는 직접 파일 업로드
scp -r /local/path user@server:/opt/recruit-ai
```

### 4. 환경 변수 파일 생성

```bash
cd /opt/recruit-ai
cp .env.prod.example .env
nano .env  # 또는 vi .env
```

#### .env 파일 수정 (필수)

```bash
RUN_MODE=prod
TZ=Asia/Seoul

# ⚠️ 수정 필수: PostgreSQL
POSTGRES_HOST=10.0.0.11
POSTGRES_PORT=5432
POSTGRES_DB=recruit
POSTGRES_USER=recruit_app
POSTGRES_PASSWORD=<강력한비밀번호>

# ⚠️ 수정 필수: Oracle
ORACLE_HOST=10.0.0.21
ORACLE_PORT=1521
ORACLE_SERVICE=ORCLPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=<강력한비밀번호>

# ⚠️ 수정 필수: OpenSearch
OPENSEARCH_URL=http://10.0.0.12:9200
# 보안 활성화 시 주석 해제
# OPENSEARCH_USER=admin
# OPENSEARCH_PASSWORD=<강력한비밀번호>
OPENSEARCH_INITIAL_ADMIN_PASSWORD=MyStrongP@ssw0rd123!

# LLM 설정 (Optional)
LLM8B_URL=http://10.0.0.13:8001/v1/chat/completions
LLM70B_URL=http://10.0.0.14:8002/v1/chat/completions
LLM8B_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
LLM70B_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
LLM_API_KEY=

# Frontend
VITE_API_BASE=http://backend:8000
```

### 5. 환경 변수 파일 보안

```bash
# 권한 설정 (읽기 전용)
chmod 600 .env

# 소유권 확인
ls -la .env
```

---

## PostgreSQL 설정

### 1. 필수 테이블 생성

PostgreSQL에 다음 테이블들을 생성해야 합니다:

- `app.recruitment` - 채용 데이터 메인 테이블
- `app.recruitment_stage` - 스테이지 테이블 (원자적 교체용)
- `app.run_history` - ETL 실행 이력
- `app.error_log` - 에러 로그

#### 방법 1: SQL 스크립트 실행

```bash
# PostgreSQL 서버에 접속하여 테이블 생성
psql -h 10.0.0.11 -U recruit_app -d recruit -f db/init/02_create_app_schema.sql
```

#### 방법 2: 수동 생성

```sql
-- app 스키마 생성
CREATE SCHEMA IF NOT EXISTS app;

-- recruitment 테이블
CREATE TABLE IF NOT EXISTS app.recruitment (
    id SERIAL PRIMARY KEY,
    candidate_id VARCHAR(50),
    full_name VARCHAR(200),
    gender VARCHAR(10),
    birth_year INTEGER,
    education_level VARCHAR(100),
    years_experience INTEGER,
    industry VARCHAR(100),
    role_title VARCHAR(200),
    resume_text TEXT,
    source_updated_at TIMESTAMP,
    load_date DATE DEFAULT CURRENT_DATE
);

-- recruitment_stage 테이블 (동일 구조)
CREATE TABLE IF NOT EXISTS app.recruitment_stage (LIKE app.recruitment INCLUDING ALL);

-- run_history 테이블
CREATE TABLE IF NOT EXISTS app.run_history (
    run_id SERIAL PRIMARY KEY,
    dag_id VARCHAR(100),
    task_id VARCHAR(100),
    source_table VARCHAR(100),
    target_table VARCHAR(100),
    status VARCHAR(20),
    rows_read INTEGER,
    rows_written INTEGER,
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    duration_ms INTEGER,
    message TEXT
);

-- error_log 테이블
CREATE TABLE IF NOT EXISTS app.error_log (
    error_id SERIAL PRIMARY KEY,
    run_id INTEGER REFERENCES app.run_history(run_id),
    dag_id VARCHAR(100),
    task_id VARCHAR(100),
    step VARCHAR(50),
    error_class VARCHAR(200),
    error_message TEXT,
    stacktrace TEXT,
    source_table VARCHAR(100),
    target_table VARCHAR(100),
    error_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 2. 권한 부여

```sql
GRANT ALL PRIVILEGES ON SCHEMA app TO recruit_app;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA app TO recruit_app;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA app TO recruit_app;
```

### 3. 테이블 확인

```sql
SELECT schemaname, tablename
FROM pg_tables
WHERE schemaname = 'app'
ORDER BY tablename;
```

---

## OpenSearch 설정

### 운영 환경 주요 수정 사항

#### 1. 보안 설정 (필수)

⚠️ **개발 환경 (위험)**:
```yaml
environment:
  - plugins.security.disabled=true
```

✅ **운영 환경 (권장)**:
```yaml
environment:
  - plugins.security.disabled=false
  - plugins.security.ssl.http.enabled=true
```

#### 2. 클러스터 모드

⚠️ **개발 환경**:
```yaml
environment:
  - discovery.type=single-node
```

✅ **운영 환경 (3노드 클러스터)**:
```yaml
environment:
  - discovery.type=multi-node
  - cluster.name=recruit-opensearch-cluster
  - node.name=opensearch-node-1
  - discovery.seed_hosts=opensearch-node-1,opensearch-node-2,opensearch-node-3
```

#### 3. 메모리 설정

⚠️ **개발 환경 (1GB)**:
```yaml
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
```

✅ **운영 환경 (32GB 서버 예시 → 16GB 힙)**:
```yaml
environment:
  - "OPENSEARCH_JAVA_OPTS=-Xms16g -Xmx16g"
```

#### 4. 인덱스 설정

파일: `airflow/dags/scripts/postgres_to_opensearch_etl.py`

⚠️ **개발 환경**:
```python
"settings": {
    "number_of_shards": 1,
    "number_of_replicas": 0
}
```

✅ **운영 환경**:
```python
"settings": {
    "number_of_shards": 3,      # 데이터 분산
    "number_of_replicas": 1     # 고가용성
}
```

#### 5. 배포 전략

⚠️ **현재 방식 (다운타임 발생)**:
```python
os_client.indices.delete(index="candidates")  # 서비스 중단
os_client.indices.create(index="candidates", body=index_body)
```

✅ **권장: Blue-Green 배포**:
```python
# 1. 새 인덱스 생성
new_index = f"candidates_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
os_client.indices.create(index=new_index, body=index_body)

# 2. 데이터 적재
bulk(os_client, actions, chunk_size=BATCH_SIZE)

# 3. alias 전환 (무중단)
os_client.indices.update_aliases({
    "actions": [
        {"remove": {"index": old_index, "alias": "candidates"}},
        {"add": {"index": new_index, "alias": "candidates"}}
    ]
})
```

### 환경 변수 설정

.env 파일에 추가:
```bash
# OpenSearch 연결
OPENSEARCH_URL=http://10.0.0.12:9200

# 보안 활성화 시
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=MyStrongPassword123!
```

---

## Airflow 배포

### 1. 배포 스크립트 실행

```bash
cd /opt/recruit-ai
chmod +x deploy_airflow_prod.sh

# Windows에서 작성된 경우 줄바꿈 변환
sudo apt install dos2unix -y
dos2unix deploy_airflow_prod.sh

# 배포 실행
./deploy_airflow_prod.sh
```

### 2. Admin 계정 설정

배포 중 프롬프트:
```
Airflow Admin Username (기본값: admin): admin
Airflow Admin Password: ********
```

### 3. 컨테이너 확인

```bash
docker ps
```

예상 출력:
```
CONTAINER ID   IMAGE                      STATUS         PORTS
abc123         airflow-webserver          Up 2 minutes   0.0.0.0:8081->8080/tcp
def456         airflow-scheduler          Up 2 minutes
```

### 4. Airflow UI 접속

```
http://<서버IP>:8081
```

### 5. DAG 확인

운영 환경에서 실행되는 DAG:

| DAG ID | 스케줄 | 설명 |
|--------|--------|------|
| `etl_oracle_to_postgres_recruit_daily` | 02:30 | Oracle → PostgreSQL ETL |
| `etl_postgres_to_opensearch_daily` | 04:00 | PostgreSQL → OpenSearch 벡터 인덱싱 |

---

## Backend/Frontend 배포

### 1. 전체 스택 실행

```bash
cd /opt/recruit-ai

# 운영 모드로 전체 실행
docker compose -f docker-compose.yml -f docker-compose.prod.yml --env-file .env up -d
```

### 2. 서비스 확인

```bash
# 전체 컨테이너 상태
docker ps

# 예상 출력
# - postgres (로컬 사용 시)
# - opensearch (로컬 사용 시)
# - airflow-webserver
# - airflow-scheduler
# - backend
# - frontend
```

### 3. OpenSearch 인덱스 초기화

```bash
# Backend 컨테이너에서 OpenSearch 인덱스 생성
docker compose exec backend python scripts/bootstrap_search.py
```

### 4. 서비스 접속 확인

```bash
# Backend API
curl http://localhost:8000/docs

# Frontend
curl http://localhost:5173

# Airflow
curl http://localhost:8081
```

---

## 배포 후 검증

### 1. Airflow ETL 테스트

#### Oracle → PostgreSQL ETL

1. Airflow UI 접속: `http://<서버IP>:8081`
2. `etl_oracle_to_postgres_recruit_daily` DAG 클릭
3. "Trigger DAG" 버튼 클릭
4. Task 실행 확인:
   - `log_start` → `extract_all` → `stage_load` → `swap_replace` → `log_success` → `cleanup_3y` → `end`

#### PostgreSQL 데이터 확인

```sql
-- PostgreSQL 접속
psql -h 10.0.0.11 -U recruit_app -d recruit

-- 데이터 건수 확인
SELECT COUNT(*) FROM app.recruitment;

-- 샘플 데이터
SELECT id, candidate_id, full_name, role_title, load_date
FROM app.recruitment
LIMIT 10;

-- 실행 이력
SELECT run_id, dag_id, status, rows_read, rows_written, duration_ms, started_at, finished_at
FROM app.run_history
ORDER BY run_id DESC
LIMIT 5;
```

### 2. 벡터 인덱싱 테스트

#### PostgreSQL → OpenSearch ETL

1. Airflow UI에서 `etl_postgres_to_opensearch_daily` DAG 실행
2. Task 실행 확인:
   - `log_start` → `extract_from_postgres` → `transform_and_index_to_opensearch` → `log_success` → `end`

#### OpenSearch 인덱스 확인

```bash
# 인덱스 존재 확인
curl http://10.0.0.12:9200/_cat/indices

# 문서 건수 확인
curl http://10.0.0.12:9200/candidates/_count

# 샘플 문서 조회
curl http://10.0.0.12:9200/candidates/_search?size=3
```

### 3. Backend API 테스트

```bash
# 검색 API 테스트
curl -X POST http://localhost:8000/search/hybrid \
  -H "Content-Type: application/json" \
  -d '{"query": "Python 개발자", "top_k": 5}'
```

### 4. Frontend 테스트

브라우저에서 `http://<서버IP>:5173` 접속하여:
- [ ] 검색 기능 동작 확인
- [ ] 검색 결과 표시 확인
- [ ] LLM 응답 확인 (설정한 경우)

---

## 운영 관리

### 1. 자동 시작 설정

시스템 재부팅 시 자동 시작:

```bash
# Docker 서비스 자동 시작
sudo systemctl enable docker

# Systemd 서비스 파일 생성
sudo nano /etc/systemd/system/recruit-ai.service
```

내용:
```ini
[Unit]
Description=Recruit AI Docker Compose Service
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/recruit-ai
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose stop
User=<your-username>

[Install]
WantedBy=multi-user.target
```

```bash
# 서비스 활성화
sudo systemctl daemon-reload
sudo systemctl enable recruit-ai.service
sudo systemctl start recruit-ai.service
```

### 2. 방화벽 설정

```bash
# UFW 방화벽 사용 시
sudo ufw allow 8081/tcp  # Airflow
sudo ufw allow 8000/tcp  # Backend
sudo ufw allow 5173/tcp  # Frontend

# 특정 IP만 허용 (권장)
sudo ufw allow from <사무실IP> to any port 8081 proto tcp
```

### 3. 로그 관리

```bash
# 로그 확인
docker compose logs -f airflow-scheduler
docker compose logs -f backend

# 로그 로테이션 설정
sudo nano /etc/logrotate.d/docker-recruit-ai
```

내용:
```
/var/lib/docker/containers/*/*.log {
  rotate 7
  daily
  compress
  missingok
  delaycompress
  copytruncate
}
```

### 4. 일상 운영 명령어

```bash
# 서비스 상태 확인
docker compose ps

# 특정 서비스 재시작
docker compose restart airflow-scheduler

# 전체 재시작
docker compose restart

# 로그 실시간 확인
docker compose logs -f

# 컨테이너 내부 접속
docker compose exec airflow-scheduler bash
docker compose exec backend bash
```

---

## 트러블슈팅

### 문제 1: Oracle 연결 실패

**증상**:
```
ERROR: [Errno -5] No address associated with hostname
```

**해결**:
```bash
# Oracle 연결 테스트
telnet 10.0.0.21 1521
nc -zv 10.0.0.21 1521

# 환경변수 확인
docker compose exec airflow-scheduler env | grep ORACLE
```

### 문제 2: PostgreSQL 연결 실패

**증상**:
```
ERROR: connection to server failed
```

**해결**:
```bash
# PostgreSQL 연결 테스트
psql -h 10.0.0.11 -U recruit_app -d recruit

# 방화벽 확인
nc -zv 10.0.0.11 5432
```

### 문제 3: OpenSearch 인덱싱 실패

**증상**:
```
ERROR: Connection refused
```

**해결**:
```bash
# OpenSearch 상태 확인
curl http://10.0.0.12:9200/_cluster/health

# 인증 정보 확인 (보안 활성화 시)
curl -u admin:password http://10.0.0.12:9200/_cluster/health
```

### 문제 4: DAG가 보이지 않음

**해결**:
```bash
# Scheduler 재시작
docker compose restart airflow-scheduler

# DAG 파일 확인
docker compose exec airflow-scheduler ls -la /opt/airflow/dags/

# DAG 문법 오류 확인
docker compose exec airflow-scheduler python /opt/airflow/dags/etl_oracle_to_postgres_recruit_daily.py
```

### 문제 5: 디스크 공간 부족

**해결**:
```bash
# 디스크 사용량 확인
df -h

# Docker 리소스 정리
docker system prune -a

# 로그 파일 정리
docker compose exec airflow-scheduler find /opt/airflow/logs -type f -mtime +7 -delete
```

---

## 보안 체크리스트

배포 후 반드시 확인:

- [ ] `.env` 파일 권한 설정: `chmod 600 .env`
- [ ] OpenSearch 보안 활성화 (`plugins.security.disabled=false`)
- [ ] 강력한 비밀번호 사용 (20자 이상, 특수문자 포함)
- [ ] 방화벽 설정 (필요한 IP만 허용)
- [ ] PostgreSQL/Oracle 방화벽 확인
- [ ] SSH 키 기반 인증 사용
- [ ] fail2ban 설치 (무차별 대입 공격 방어)

```bash
sudo apt install fail2ban -y
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

---

## 모니터링

### 1. Airflow 모니터링

- **URL**: `http://<서버IP>:8081`
- **확인 항목**:
  - DAG 실행 상태
  - Task 성공/실패 여부
  - 실행 이력 그래프

### 2. PostgreSQL 모니터링

```sql
-- 실행 이력
SELECT * FROM app.run_history ORDER BY run_id DESC LIMIT 10;

-- 에러 로그
SELECT * FROM app.error_log ORDER BY error_id DESC LIMIT 10;

-- 테이블 크기
SELECT pg_size_pretty(pg_total_relation_size('app.recruitment'));
```

### 3. OpenSearch 모니터링

```bash
# 클러스터 상태
curl http://10.0.0.12:9200/_cluster/health?pretty

# 노드 통계
curl http://10.0.0.12:9200/_nodes/stats?pretty

# 인덱스 통계
curl http://10.0.0.12:9200/candidates/_stats?pretty
```

### 4. 시스템 리소스 모니터링

```bash
# CPU/메모리 확인
htop

# 디스크 사용량
df -h

# Docker 리소스 사용량
docker stats
```

---

## 참고 문서

- [README.md](README.md) - 프로젝트 개요
- [.env.prod.example](.env.prod.example) - 환경 변수 예시
- [deploy_airflow_prod.sh](deploy_airflow_prod.sh) - 배포 스크립트

---

**배포 완료! 문제 발생 시 위 트러블슈팅 섹션을 참고하거나 로그를 확인하세요.**
