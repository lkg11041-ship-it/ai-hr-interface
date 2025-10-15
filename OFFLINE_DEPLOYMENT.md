# 폐쇄망(Air-Gapped) 환경 배포 가이드

이 문서는 인터넷이 차단된 폐쇄망 환경에서 Recruit AI Airflow 시스템을 배포하는 방법을 설명합니다.

## 📋 목차

1. [개요](#개요)
2. [배포 프로세스 요약](#배포-프로세스-요약)
3. [사전 준비 (인터넷 연결 환경)](#사전-준비-인터넷-연결-환경)
4. [이미지 준비 (인터넷 연결 환경)](#이미지-준비-인터넷-연결-환경)
5. [파일 전송](#파일-전송)
6. [폐쇄망 서버 배포](#폐쇄망-서버-배포)
7. [배포 후 검증](#배포-후-검증)
8. [트러블슈팅](#트러블슈팅)

---

## 개요

### 폐쇄망 배포의 특징

폐쇄망 환경에서는 다음 제약사항이 있습니다:

- ❌ Docker Hub에서 이미지 다운로드 불가
- ❌ PyPI에서 Python 패키지 설치 불가
- ❌ HuggingFace에서 ML 모델 다운로드 불가
- ❌ 외부 API 호출 불가

### 솔루션

이 가이드는 다음 방법으로 문제를 해결합니다:

- ✅ 사전 빌드된 Docker 이미지 사용 (모든 의존성 포함)
- ✅ Python 패키지를 이미지에 포함
- ✅ 임베딩 모델을 이미지에 미리 다운로드
- ✅ 로컬 이미지만 사용 (`pull_policy: never`)

---

## 배포 프로세스 요약

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 1: 인터넷 연결 환경 (개발자 PC / 빌드 서버)          │
├─────────────────────────────────────────────────────────────┤
│  1. Docker 이미지 빌드                                       │
│     - Airflow (Python 패키지 + 임베딩 모델 포함)             │
│     - Backend, Frontend (Optional)                          │
│  2. 이미지를 tar 파일로 저장                                 │
│  3. 프로젝트 파일 압축                                       │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      │  USB / 내부망 파일 공유 / SCP
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│  Phase 2: 폐쇄망 환경 (운영 서버)                           │
├─────────────────────────────────────────────────────────────┤
│  1. tar 파일 전송 확인                                       │
│  2. Docker 이미지 로드 (docker load)                        │
│  3. 환경 변수 설정 (.env)                                    │
│  4. docker-compose.offline.yml로 배포                       │
│  5. 서비스 확인                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## 사전 준비 (인터넷 연결 환경)

### 1. 필수 소프트웨어 설치

**개발 PC 또는 빌드 서버**에서:

```bash
# Docker 설치
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Docker Compose 설치
sudo apt install docker-compose-plugin -y

# 버전 확인
docker --version
docker compose version
```

### 2. 프로젝트 다운로드

```bash
# Git Clone
git clone <your-repo-url> recruit-ai
cd recruit-ai

# 또는 소스 파일 다운로드
```

### 3. 디스크 공간 확인

```bash
# 최소 15GB 이상 필요
df -h

# 예상 용량:
# - Base 이미지: ~5GB
# - Airflow 이미지 (빌드 후): ~3GB
# - Backend/Frontend: ~2GB
# - 여유 공간: ~5GB
```

---

## 이미지 준비 (인터넷 연결 환경)

### 방법 1: 자동 스크립트 사용 (권장)

```bash
cd recruit-ai

# 스크립트 실행 권한 부여
chmod +x scripts/prepare-offline-images.sh

# 이미지 빌드 및 저장
./scripts/prepare-offline-images.sh
```

**스크립트 실행 내용**:
1. Base 이미지 다운로드 (apache/airflow, postgres, opensearch)
2. Airflow 커스텀 이미지 빌드 (Python 패키지 + 임베딩 모델 포함)
3. Backend/Frontend 이미지 빌드
4. 모든 이미지를 tar 파일로 저장
5. 폐쇄망 배포용 스크립트 생성

**출력 위치**: `offline-images/` 디렉토리

### 방법 2: 수동 빌드

#### Step 1: Base 이미지 다운로드

```bash
# Base 이미지 pull
docker pull apache/airflow:2.9.2-python3.11
docker pull postgres:16
docker pull opensearchproject/opensearch:2.13.0
docker pull opensearchproject/opensearch-dashboards:2.13.0

# tar 파일로 저장
mkdir -p offline-images
docker save apache/airflow:2.9.2-python3.11 -o offline-images/apache-airflow.tar
docker save postgres:16 -o offline-images/postgres.tar
docker save opensearchproject/opensearch:2.13.0 -o offline-images/opensearch.tar
docker save opensearchproject/opensearch-dashboards:2.13.0 -o offline-images/opensearch-dashboards.tar
```

#### Step 2: Airflow 커스텀 이미지 빌드

```bash
# Airflow 이미지 빌드 (Python 패키지 + 임베딩 모델 포함)
cd recruit-ai
docker build -f airflow/Dockerfile.offline -t recruit-airflow:offline ./airflow

# tar 파일로 저장
docker save recruit-airflow:offline -o offline-images/recruit-airflow-offline.tar
```

#### Step 3: Backend/Frontend 이미지 빌드 (Optional)

```bash
# Backend 빌드
docker build -t recruit-backend:offline ./backend
docker save recruit-backend:offline -o offline-images/recruit-backend-offline.tar

# Frontend 빌드
docker build -t recruit-frontend:offline ./frontend
docker save recruit-frontend:offline -o offline-images/recruit-frontend-offline.tar
```

### 이미지 확인

```bash
# 생성된 tar 파일 확인
ls -lh offline-images/

# 예상 출력:
# apache-airflow.tar              (~2.5GB)
# postgres.tar                    (~150MB)
# opensearch.tar                  (~800MB)
# opensearch-dashboards.tar       (~400MB)
# recruit-airflow-offline.tar     (~3GB)
# recruit-backend-offline.tar     (~1GB)
# recruit-frontend-offline.tar    (~500MB)
```

---

## 파일 전송

### 1. 전송 파일 목록

```bash
offline-images/           # Docker 이미지 tar 파일들
airflow/                  # Airflow DAG 및 스크립트
backend/                  # Backend 소스 (Optional)
frontend/                 # Frontend 소스 (Optional)
db/                       # 초기 DB 스키마
scripts/                  # 배포 스크립트
docker-compose.yml        # 기본 compose 파일
docker-compose.offline.yml # 폐쇄망 전용 compose 파일
.env.prod.example         # 환경 변수 예시
```

### 2. 파일 압축

```bash
cd recruit-ai

# 전체 프로젝트 압축 (이미지 포함)
tar -czf recruit-ai-offline-$(date +%Y%m%d).tar.gz \
    offline-images/ \
    airflow/ \
    backend/ \
    frontend/ \
    db/ \
    scripts/ \
    infra/ \
    docker-compose.yml \
    docker-compose.offline.yml \
    .env.prod.example

# 파일 크기 확인
ls -lh recruit-ai-offline-*.tar.gz
```

### 3. 폐쇄망 서버로 전송

#### 방법 A: USB 드라이브

```bash
# USB 마운트 확인
lsblk

# USB로 복사
cp recruit-ai-offline-*.tar.gz /media/usb/
sync  # 버퍼 플러시
```

#### 방법 B: 내부망 파일 공유

```bash
# SMB/NFS 공유 폴더에 복사
cp recruit-ai-offline-*.tar.gz /mnt/share/
```

#### 방법 C: SCP (내부망 연결 가능 시)

```bash
# 폐쇄망 서버로 전송
scp recruit-ai-offline-*.tar.gz user@offline-server:/opt/
```

---

## 폐쇄망 서버 배포

### 1. 파일 압축 해제

```bash
# 폐쇄망 서버 접속
ssh user@offline-server

# 작업 디렉토리로 이동
cd /opt

# 파일 압축 해제
tar -xzf recruit-ai-offline-*.tar.gz
cd recruit-ai
```

### 2. Docker 이미지 로드

#### 자동 로드 (권장)

```bash
cd offline-images
chmod +x load-images.sh
./load-images.sh
```

#### 수동 로드

```bash
cd offline-images

# 모든 tar 파일 로드
for tar_file in *.tar; do
    echo "Loading $tar_file..."
    docker load -i "$tar_file"
done
```

### 3. 이미지 로드 확인

```bash
# 로드된 이미지 확인
docker images

# 예상 출력:
# REPOSITORY                        TAG       IMAGE ID       SIZE
# recruit-airflow                   offline   abc123...      3GB
# recruit-backend                   offline   def456...      1GB
# recruit-frontend                  offline   ghi789...      500MB
# apache/airflow                    2.9.2...  ...            2.5GB
# postgres                          16        ...            150MB
# opensearchproject/opensearch      2.13.0    ...            800MB
```

### 4. 환경 변수 설정

```bash
cd /opt/recruit-ai

# .env 파일 생성
cp .env.prod.example .env
nano .env  # 또는 vi .env
```

#### .env 파일 수정 (필수)

```bash
RUN_MODE=prod
TZ=Asia/Seoul

# PostgreSQL (외부 DB)
POSTGRES_HOST=10.0.0.11
POSTGRES_PORT=5432
POSTGRES_DB=recruit
POSTGRES_USER=recruit_app
POSTGRES_PASSWORD=<강력한비밀번호>

# Oracle (외부 DB)
ORACLE_HOST=10.0.0.21
ORACLE_PORT=1521
ORACLE_SERVICE=ORCLPDB1
ORACLE_USER=hr
ORACLE_PASSWORD=<강력한비밀번호>

# OpenSearch (외부 클러스터)
OPENSEARCH_URL=http://10.0.0.12:9200
# 보안 활성화 시
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=<강력한비밀번호>

# Airflow Admin 계정
AIRFLOW_ADMIN_USER=admin
AIRFLOW_ADMIN_PASSWORD=<강력한비밀번호>

# 포트 설정 (Optional)
AIRFLOW_PORT=8081
BACKEND_PORT=8000
FRONTEND_PORT=5173
```

### 5. PostgreSQL 테이블 생성

```bash
# PostgreSQL에 필수 테이블 생성
psql -h 10.0.0.11 -U recruit_app -d recruit -f db/init/02_create_app_schema.sql
```

### 6. 서비스 배포

```bash
cd /opt/recruit-ai

# 폐쇄망 모드로 배포 (외부 DB 사용)
docker compose -f docker-compose.yml -f docker-compose.offline.yml --env-file .env up -d

# 로그 확인
docker compose logs -f
```

### 7. 서비스 확인

```bash
# 컨테이너 상태 확인
docker compose ps

# 예상 출력:
# NAME                  STATUS          PORTS
# airflow-webserver     Up (healthy)    0.0.0.0:8081->8080/tcp
# airflow-scheduler     Up
# backend               Up              0.0.0.0:8000->8000/tcp
# frontend              Up              0.0.0.0:5173->5173/tcp
```

---

## 배포 후 검증

### 1. Airflow 접속

```bash
# 브라우저에서 접속
http://<폐쇄망서버IP>:8081

# 또는 curl로 확인
curl http://localhost:8081/health
```

**로그인 정보**:
- Username: `.env`의 `AIRFLOW_ADMIN_USER` (기본: admin)
- Password: `.env`의 `AIRFLOW_ADMIN_PASSWORD`

### 2. DAG 확인

Airflow UI에서 다음 DAG 확인:
- `etl_oracle_to_postgres_recruit_daily` (02:30)
- `etl_postgres_to_opensearch_daily` (04:00)

### 3. DAG 수동 실행 테스트

1. Airflow UI → DAGs 메뉴
2. `etl_oracle_to_postgres_recruit_daily` 클릭
3. "Trigger DAG" 버튼 클릭
4. Task 실행 상태 확인

### 4. 임베딩 모델 확인

```bash
# Airflow Scheduler 컨테이너 접속
docker compose exec airflow-scheduler bash

# 임베딩 모델 캐시 확인
ls -lh /opt/airflow/.cache/huggingface/
ls -lh /opt/airflow/.cache/sentence_transformers/

# Python에서 모델 로드 테스트
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
print('Model loaded successfully!')
print(f'Embedding dimension: {model.get_sentence_embedding_dimension()}')
"
```

예상 출력:
```
Model loaded successfully!
Embedding dimension: 384
```

### 5. Backend/Frontend 확인

```bash
# Backend API
curl http://localhost:8000/docs

# Frontend
curl http://localhost:5173
```

---

## 트러블슈팅

### 문제 1: 이미지 로드 실패

**증상**:
```
Error response from daemon: open /var/lib/docker/tmp/...tar: no such file or directory
```

**해결**:
```bash
# tar 파일 무결성 확인
tar -tzf recruit-airflow-offline.tar | head

# 파일 권한 확인
ls -lh offline-images/*.tar

# 수동 로드 재시도
docker load -i offline-images/recruit-airflow-offline.tar
```

### 문제 2: 컨테이너 pull 시도

**증상**:
```
Error response from daemon: pull access denied for recruit-airflow
```

**원인**: `pull_policy: never`가 설정되지 않음

**해결**:
```bash
# docker-compose.offline.yml 사용 확인
docker compose -f docker-compose.yml -f docker-compose.offline.yml config | grep pull_policy

# 모든 서비스에 pull_policy: never가 있어야 함
```

### 문제 3: 임베딩 모델 다운로드 시도

**증상**:
```
HTTPError: 403 Forbidden for url: https://huggingface.co/...
```

**원인**: 환경 변수 미설정으로 인터넷에서 모델 다운로드 시도

**해결**:
```bash
# Airflow Scheduler 환경 변수 확인
docker compose exec airflow-scheduler env | grep -E "(TRANSFORMERS|HF_|SENTENCE)"

# 출력 예시:
# TRANSFORMERS_CACHE=/opt/airflow/.cache/huggingface
# HF_HOME=/opt/airflow/.cache/huggingface
# SENTENCE_TRANSFORMERS_HOME=/opt/airflow/.cache/sentence_transformers

# 캐시 디렉토리 확인
docker compose exec airflow-scheduler ls -la /opt/airflow/.cache/
```

### 문제 4: 디스크 공간 부족

**증상**:
```
Error: No space left on device
```

**해결**:
```bash
# 디스크 사용량 확인
df -h

# Docker 리소스 정리
docker system prune -a

# 사용하지 않는 이미지 삭제
docker images -f "dangling=true" -q | xargs docker rmi

# 볼륨 정리 (주의: 데이터 손실 가능)
docker volume prune
```

### 문제 5: 네트워크 연결 실패

**증상**:
```
ERROR: Could not connect to Oracle/PostgreSQL/OpenSearch
```

**해결**:
```bash
# 컨테이너 내부에서 연결 테스트
docker compose exec airflow-scheduler bash

# Oracle 연결 테스트
telnet $ORACLE_HOST $ORACLE_PORT

# PostgreSQL 연결 테스트
psql -h $POSTGRES_HOST -U $POSTGRES_USER -d $POSTGRES_DB -c "SELECT 1"

# OpenSearch 연결 테스트
curl $OPENSEARCH_URL
```

### 문제 6: Python 패키지 누락

**증상**:
```
ModuleNotFoundError: No module named 'xxx'
```

**해결**:
```bash
# 컨테이너에서 설치된 패키지 확인
docker compose exec airflow-scheduler pip list

# 필요 시 이미지 재빌드 (인터넷 연결 환경에서)
# requirements-offline.txt에 패키지 추가 후 재빌드
```

---

## 보안 고려사항

### 1. 이미지 스캔

배포 전 이미지 취약점 스캔 (인터넷 연결 환경):

```bash
# Trivy 설치 (선택)
curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin

# 이미지 스캔
trivy image recruit-airflow:offline
```

### 2. 비밀번호 관리

```bash
# .env 파일 권한 설정
chmod 600 .env

# 강력한 비밀번호 생성
openssl rand -base64 32
```

### 3. 네트워크 격리

```bash
# Docker 네트워크 확인
docker network ls

# 격리된 네트워크 사용 (docker-compose.offline.yml에 설정됨)
```

---

## 업데이트 절차

### 새 버전 배포

1. **인터넷 연결 환경**에서 새 이미지 빌드
2. tar 파일로 저장
3. 폐쇄망으로 전송
4. 이미지 로드 및 재배포

```bash
# 폐쇄망 서버에서
cd /opt/recruit-ai

# 기존 서비스 중지
docker compose down

# 새 이미지 로드
docker load -i /path/to/new-image.tar

# 서비스 재시작
docker compose -f docker-compose.yml -f docker-compose.offline.yml up -d
```

---

## 체크리스트

### 인터넷 연결 환경 (빌드 서버)

- [ ] Docker 및 Docker Compose 설치
- [ ] 프로젝트 소스 다운로드
- [ ] 디스크 공간 확인 (15GB 이상)
- [ ] `prepare-offline-images.sh` 실행
- [ ] 모든 tar 파일 생성 확인
- [ ] 프로젝트 파일 압축
- [ ] 파일 전송

### 폐쇄망 환경 (운영 서버)

- [ ] Docker 설치 확인
- [ ] 전송된 파일 압축 해제
- [ ] Docker 이미지 로드
- [ ] 이미지 로드 확인 (`docker images`)
- [ ] .env 파일 설정
- [ ] PostgreSQL 테이블 생성
- [ ] `docker-compose.offline.yml`로 배포
- [ ] 컨테이너 상태 확인
- [ ] Airflow UI 접속 확인
- [ ] DAG 확인 및 테스트
- [ ] 임베딩 모델 로드 확인

---

## 참고 문서

- [Dockerfile.offline](airflow/Dockerfile.offline) - 폐쇄망 전용 Dockerfile
- [docker-compose.offline.yml](docker-compose.offline.yml) - 폐쇄망 전용 Compose 파일
- [requirements-offline.txt](airflow/requirements-offline.txt) - Python 의존성 목록
- [prepare-offline-images.sh](scripts/prepare-offline-images.sh) - 이미지 준비 스크립트
- [PRODUCTION_DEPLOYMENT.md](PRODUCTION_DEPLOYMENT.md) - 일반 운영 배포 가이드

---

**폐쇄망 배포 완료! 문제 발생 시 위 트러블슈팅 섹션을 참고하세요.**
