# Oracle 11g 폐쇄망 배포 가이드

## 개요

이 문서는 Oracle 11g 데이터베이스와 연동하는 Airflow ETL 시스템을 폐쇄망 환경에 배포하는 방법을 설명합니다.

### 주요 변경사항

- **Oracle Thick Mode 사용**: Oracle 11g는 python-oracledb Thin mode를 지원하지 않으므로 Thick mode 필수
- **Oracle Instant Client 21.13 포함**: Docker 이미지에 Oracle Client 라이브러리 포함
- **자동 다운로드**: 인터넷 환경에서 이미지 빌드 시 Oracle Instant Client 자동 다운로드

## 호환성 정보

### python-oracledb 모드별 Oracle 버전 지원

| 모드 | 지원 Oracle 버전 | Oracle Client 필요 |
|------|-----------------|-------------------|
| **Thin Mode** | 12.1, 18c, 19c, 21c, 23c | 불필요 (Pure Python) |
| **Thick Mode** | 9.2, 10g, **11.2g**, 12c, 18c, 19c, 21c, 23c | 필요 (Instant Client) |

**결론**: Oracle 11g를 사용하려면 반드시 **Thick Mode**가 필요합니다.

## 폐쇄망 배포 절차

### 1단계: 인터넷 연결 환경에서 Docker 이미지 빌드

```bash
# 프로젝트 루트 디렉토리에서 실행
cd /path/to/recruit-ai-starter-dualmode

# Oracle Instant Client를 포함한 이미지 빌드
docker build -f airflow/Dockerfile.offline -t recruit-airflow:offline ./airflow
```

**빌드 과정에서 수행되는 작업**:
1. Oracle Instant Client 21.13 다운로드 (약 80MB)
2. libaio1 등 시스템 라이브러리 설치
3. python-oracledb 2.0.1 설치
4. Thick mode 초기화 코드 포함

**예상 빌드 시간**: 5-10분 (네트워크 속도에 따라 다름)

### 2단계: Docker 이미지를 tar 파일로 저장

```bash
# 이미지를 파일로 저장 (약 1.5GB)
docker save recruit-airflow:offline -o recruit-airflow-offline.tar

# 파일 크기 확인
ls -lh recruit-airflow-offline.tar
```

### 3단계: 폐쇄망 서버로 파일 전송

```bash
# 방법 1: USB 드라이브 사용
cp recruit-airflow-offline.tar /media/usb/

# 방법 2: SCP 사용 (망분리 구간에서 허용된 경우)
scp recruit-airflow-offline.tar user@offline-server:/path/to/destination/
```

**함께 전송해야 할 파일**:
- `recruit-airflow-offline.tar` (Docker 이미지)
- `docker-compose.offline.yml` (배포 설정)
- `.env.offline` (환경 변수 템플릿)
- `airflow/dags/` (DAG 파일들)

### 4단계: 폐쇄망 서버에서 이미지 로드

```bash
# 폐쇄망 서버에 로그인 후

# Docker 이미지 로드
docker load -i recruit-airflow-offline.tar

# 이미지 확인
docker images | grep recruit-airflow
# 출력 예: recruit-airflow   offline   abc123def456   5 minutes ago   1.5GB
```

### 5단계: 환경 설정 파일 작성

```bash
# .env 파일 생성
cp .env.offline .env

# 환경에 맞게 설정 수정
vim .env
```

**필수 설정 항목**:

```bash
# PostgreSQL 설정
POSTGRES_HOST=10.149.172.233
POSTGRES_PORT=5432
POSTGRES_DB=rsaidb
POSTGRES_USER=rs_ai_user
POSTGRES_PASSWORD="tlstprP1@#"

# Oracle 설정 (Oracle 11g)
ORACLE_HOST=10.253.41.229
ORACLE_PORT=1521
ORACLE_SERVICE=RECU              # SERVICE_NAME 또는 SID
ORACLE_USER=IF_IC0_TEMP_USER
ORACLE_PASSWORD="eykk1275#"
```

### 6단계: Airflow 배포

```bash
# docker-compose로 배포
docker-compose -f docker-compose.offline.yml up -d

# 컨테이너 상태 확인
docker-compose -f docker-compose.offline.yml ps

# 로그 확인
docker-compose -f docker-compose.offline.yml logs -f airflow-webserver
```

### 7단계: Oracle Thick Mode 초기화 확인

```bash
# Airflow 웹서버 컨테이너 로그에서 Thick mode 초기화 확인
docker logs airflow-webserver 2>&1 | grep "Oracle Thick Mode"
```

**정상 출력 예시**:
```
[INFO] Oracle Thick Mode initialized successfully
[INFO] Oracle Instant Client location: /opt/oracle/instantclient
[INFO] This enables Oracle 11g connectivity
```

**에러 출력 예시**:
```
[WARN] Oracle Thick Mode initialization: DPY-3001: cannot locate a 64-bit Oracle Client library
[WARN] Will attempt connection in Thin mode (may fail for Oracle 11g)...
```
→ 이 경우 Docker 이미지가 올바르게 빌드되지 않은 것입니다. 1단계부터 다시 시작하세요.

### 8단계: Oracle 연결 테스트

```bash
# 컨테이너 내부에서 Python으로 Oracle 연결 테스트
docker exec -it airflow-webserver python3 << 'EOF'
import oracledb

# Thick mode가 초기화되었는지 확인
print(f"Oracle client version: {oracledb.clientversion()}")

# Oracle 연결 시도
conn = oracledb.connect(
    user='IF_IC0_TEMP_USER',
    password='eykk1275#',
    host='10.253.41.229',
    port=1521,
    service_name='RECU'
)
print("✓ Oracle 11g connection successful!")
print(f"Oracle version: {conn.version}")
conn.close()
EOF
```

**정상 출력 예시**:
```
Oracle client version: (21, 13, 0, 0, 0)
✓ Oracle 11g connection successful!
Oracle version: 11.2.0.4.0
```

### 9단계: Airflow 웹 UI 접속

```bash
# 웹 브라우저에서 접속
http://<폐쇄망-서버-IP>:8081

# 기본 계정
ID: admin
PW: admin
```

### 10단계: DAG 실행 테스트

1. Airflow 웹 UI에서 `etl_oracle_to_postgres_recruit_daily` DAG 찾기
2. DAG 활성화 (토글 스위치 ON)
3. "Trigger DAG" 버튼 클릭하여 수동 실행
4. 로그 확인:
   - `[DEBUG] Connecting to Oracle (Thick Mode): 10.253.41.229:1521/RECU`
   - `[DEBUG] Oracle connection successful (method 1)`
   - `Extracted XXX rows from Oracle`
   - `Successfully loaded XXX rows to production table`

## 문제 해결

### 1. DPY-3001: cannot locate a 64-bit Oracle Client library

**원인**: Oracle Instant Client가 Docker 이미지에 포함되지 않음

**해결**:
```bash
# 컨테이너 내부에서 Instant Client 확인
docker exec -it airflow-webserver ls -la /opt/oracle/instantclient

# 없다면 이미지를 다시 빌드해야 함
# 1단계부터 다시 시작
```

### 2. DPY-6005 / DPY-4011: Connection reset by peer (Oracle 11g)

**원인**: Thin mode를 사용하는 경우 (Thick mode 초기화 실패)

**해결**:
```bash
# Thick mode가 제대로 초기화되었는지 확인
docker exec -it airflow-webserver python3 -c "import oracledb; print(oracledb.clientversion())"

# 에러가 나면 이미지 재빌드 필요
```

### 3. ORA-12514: TNS:listener does not currently know of service

**원인**: ORACLE_SERVICE 값이 잘못됨 (SERVICE_NAME과 SID 혼동)

**해결**:
```bash
# Oracle 서버에서 서비스명 확인
SQL> SELECT VALUE FROM V$PARAMETER WHERE NAME='service_names';

# 또는 SID로 시도
# .env 파일에서 ORACLE_SERVICE=<SID> 로 변경
```

### 4. Oracle Instant Client 버전 확인

```bash
# 컨테이너 내부에서 확인
docker exec -it airflow-webserver /opt/oracle/instantclient/sqlplus -v

# Python에서 확인
docker exec -it airflow-webserver python3 -c "import oracledb; print(oracledb.clientversion())"
```

**예상 출력**: `(21, 13, 0, 0, 0)` - Oracle Instant Client 21.13

## Oracle Instant Client 다운로드 정보

### 자동 다운로드 (Dockerfile에서)

Dockerfile.offline에서 자동으로 다운로드하는 파일:
- URL: `https://download.oracle.com/otn_software/linux/instantclient/2113000/instantclient-basic-linux.x64-21.13.0.0.0dbru.zip`
- 크기: 약 80MB
- 버전: 21.13.0.0.0
- 플랫폼: Linux x64

### 수동 다운로드 (선택사항)

인터넷 연결이 불안정하거나 방화벽 문제가 있는 경우:

1. Oracle 웹사이트 방문:
   https://www.oracle.com/database/technologies/instant-client/linux-x86-64-downloads.html

2. "instantclient-basic-linux.x64-21.13.0.0.0dbru.zip" 다운로드

3. Dockerfile.offline 수정:
   ```dockerfile
   # wget 대신 COPY 사용
   COPY instantclient-basic-linux.x64-21.13.0.0.0dbru.zip /opt/oracle/
   RUN cd /opt/oracle && \
       unzip instantclient-basic-linux.x64-21.13.0.0.0dbru.zip && \
       rm -f instantclient-basic-linux.x64-21.13.0.0.0dbru.zip && \
       mv instantclient_21_13 instantclient
   ```

## 성능 정보

### Docker 이미지 크기

- **Thin mode 이미지**: 약 1.2GB
- **Thick mode 이미지** (Oracle Instant Client 포함): 약 1.5GB
- **추가 용량**: +300MB (Oracle Instant Client)

### 메모리 사용량

- **Thin mode**: Airflow 프로세스당 약 200-300MB
- **Thick mode**: Airflow 프로세스당 약 250-350MB
- **추가 메모리**: +50MB (Oracle Client 라이브러리)

### 연결 성능

- **Thick mode가 Thin mode보다 약간 빠름** (네이티브 C 라이브러리 사용)
- Oracle 11g의 경우 Thick mode가 유일한 선택지

## 참고 자료

- python-oracledb 공식 문서: https://python-oracledb.readthedocs.io/
- Oracle Instant Client: https://www.oracle.com/database/technologies/instant-client.html
- Thick vs Thin Mode 비교: https://python-oracledb.readthedocs.io/en/latest/user_guide/appendix_b.html

## 변경 이력

- 2024-XX-XX: Oracle 11g 지원을 위해 Thick mode로 전환
- 이전: Thin mode 사용 (Oracle 12.1+ 만 지원)
