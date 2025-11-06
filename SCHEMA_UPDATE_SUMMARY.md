# Oracle 테이블 스키마 변경 적용 완료

## 변경 개요

Oracle 소스 테이블의 스키마가 변경됨에 따라 ETL 로직을 업데이트했습니다.

### 주요 변경사항

| 항목 | 이전 | 이후 |
|------|------|------|
| **Oracle 스키마** | rsaiif | SREC |
| **Oracle 테이블** | applicant_info | APPLICANT_INFO_TEMP |
| **컬럼 수** | 149개 | 155개 |
| **Primary Key** | APPLICANT_INFO_ID | PK_KEY |

### 새로 추가된 컬럼 (6개)

1. **PK_KEY** (VARCHAR2(4000)) - PRIMARY KEY
2. **NOTIYY** (VARCHAR2(4000)) - 공고년도
3. **BALNO** (VARCHAR2(10)) - 발령번호
4. **NOTINO** (VARCHAR2(50)) - 공고번호
5. **RESNO** (VARCHAR2(500)) - 주민번호
6. **SCRCOMPCD** (VARCHAR2(10)) - 심사회사코드

### 데이터 타입 변경

- **LANG1_SCORE, LANG2_SCORE, LANG3_SCORE, LANG4_SCORE**
  - 이전: VARCHAR2
  - 이후: NUMBER(38)

## 수정된 파일

### 1. oracle_recruitment_etl.py

**상수 변경** (Line 54-55):
```python
SOURCE_SCHEMA = "SREC"              # Changed from "rsaiif"
SOURCE_TABLE = "APPLICANT_INFO_TEMP"  # Changed from "applicant_info"
```

**SELECT 쿼리 업데이트** (Lines 296-331):
- 155개 컬럼 전체를 새 스키마에 맞게 수정
- PK_KEY, NOTIYY, BALNO, NOTINO, RESNO, SCRCOMPCD를 첫 6개 컬럼으로 추가
- 나머지 149개 컬럼도 순서 및 이름 확인하여 정렬

**INSERT 쿼리 업데이트** (Lines 420-473):
- PostgreSQL 타겟 테이블의 컬럼 리스트를 155개로 확장
- VALUES 절의 placeholder (%s)를 155개로 확장
- 컬럼 순서는 SELECT 쿼리와 동일하게 유지

### 2. etl_oracle_to_postgres_recruit_daily.py

**DAG 설명 업데이트** (Line 21):
```python
description='Daily ETL: Oracle SREC.APPLICANT_INFO_TEMP -> PostgreSQL rsaiif.applicant_info with full reload strategy'
```

**주석 업데이트**:
- Task 2 주석: "SREC.APPLICANT_INFO_TEMP - 155개 컬럼"
- Task Flow 주석: "Oracle (10.253.41.194:RECU/IF_IC0_TEMP_USER/SREC.APPLICANT_INFO_TEMP)"

### 3. CREATE_POSTGRES_TABLE.sql (신규 생성)

PostgreSQL 타겟 테이블 DDL을 새 스키마에 맞게 작성했습니다.

**테이블 구조**:
```sql
CREATE TABLE IF NOT EXISTS rsaiif.applicant_info
(
    pk_key                VARCHAR(4000) NOT NULL PRIMARY KEY,
    notiyy                VARCHAR(4000),
    balno                 VARCHAR(10),
    notino                VARCHAR(50),
    resno                 VARCHAR(500),
    scrcompcd             VARCHAR(10),
    company_nm            VARCHAR(4000),
    name                  VARCHAR(50),
    ...
    lang1_score           NUMERIC(38),  -- NUMBER(38) → NUMERIC(38)
    lang2_score           NUMERIC(38),
    lang3_score           NUMERIC(38),
    lang4_score           NUMERIC(38),
    ...
    reason                VARCHAR(4000),
    experience            VARCHAR(4000),
    skill                 VARCHAR(4000)
);
```

**인덱스 생성**:
```sql
CREATE INDEX IF NOT EXISTS idx_applicant_pk_key ON rsaiif.applicant_info(pk_key);
CREATE INDEX IF NOT EXISTS idx_applicant_notiyy ON rsaiif.applicant_info(notiyy);
CREATE INDEX IF NOT EXISTS idx_applicant_name ON rsaiif.applicant_info(name);
```

**권한 부여**:
```sql
GRANT SELECT, INSERT, UPDATE, DELETE ON rsaiif.applicant_info TO rs_ai_user;
```

## 배포 전 필수 작업

### 1. PostgreSQL 테이블 재생성

기존 테이블을 DROP하고 새 스키마로 재생성해야 합니다.

```bash
# PostgreSQL 서버에 접속
psql -h 10.149.172.233 -p 5432 -U rs_ai_user -d rsaidb

# 기존 테이블 백업 (필요시)
CREATE TABLE rsaiif.applicant_info_backup AS SELECT * FROM rsaiif.applicant_info;

# 기존 테이블 삭제
DROP TABLE IF EXISTS rsaiif.applicant_info CASCADE;

# 새 테이블 생성
\i CREATE_POSTGRES_TABLE.sql
```

**⚠️ 주의사항**:
- 기존 데이터는 모두 삭제됩니다
- 필요한 경우 백업을 먼저 생성하세요
- 테이블 재생성 후에 ETL을 실행하세요

### 2. Airflow DAG 재배포

```bash
# 폐쇄망 서버에서 파일 복사
cd /path/to/recruit-ai-starter-dualmode

# DAG 파일 복사 (컨테이너가 자동으로 감지)
docker cp airflow/dags/etl_oracle_to_postgres_recruit_daily.py airflow-webserver:/opt/airflow/dags/
docker cp airflow/dags/scripts/oracle_recruitment_etl.py airflow-webserver:/opt/airflow/dags/scripts/

# Airflow 웹서버 재시작 (선택사항)
docker restart airflow-webserver
```

### 3. ETL 테스트 실행

```bash
# Airflow 웹 UI 접속
http://10.149.172.233:8081

# 1. DAG 활성화 (토글 ON)
# 2. "Trigger DAG" 버튼 클릭
# 3. 로그 확인:
#    - [INFO] Connecting to Oracle (Thick Mode): 10.253.41.194:1521/RECU
#    - [INFO] Executing: SELECT * FROM SREC.APPLICANT_INFO_TEMP
#    - [INFO] Extracted XXX rows from Oracle
#    - [INFO] Successfully loaded XXX rows to production table
```

## 검증 체크리스트

배포 후 다음 사항을 확인하세요:

- [ ] PostgreSQL 테이블이 155개 컬럼으로 재생성되었는가?
- [ ] PK_KEY가 Primary Key로 설정되었는가?
- [ ] 인덱스가 생성되었는가?
- [ ] Airflow DAG가 정상적으로 로드되었는가?
- [ ] Oracle 연결이 SREC.APPLICANT_INFO_TEMP로 성공하는가?
- [ ] ETL 실행 시 155개 컬럼이 모두 이관되는가?
- [ ] run_history 테이블에 실행 이력이 기록되는가?
- [ ] 한글 데이터가 깨지지 않는가? (encoding 확인)

## 롤백 계획

문제 발생 시 이전 버전으로 롤백:

```bash
# 1. Git에서 이전 버전 체크아웃
git checkout <previous-commit-hash> airflow/dags/
git checkout <previous-commit-hash> airflow/dags/scripts/

# 2. PostgreSQL 테이블 복구
DROP TABLE rsaiif.applicant_info;
ALTER TABLE rsaiif.applicant_info_backup RENAME TO applicant_info;

# 3. Airflow 재시작
docker restart airflow-webserver airflow-scheduler
```

## 참고사항

### Oracle → PostgreSQL 컬럼 매핑

- Oracle `NUMBER(38)` → PostgreSQL `NUMERIC(38)`
- Oracle `VARCHAR2(N)` → PostgreSQL `VARCHAR(N)`
- Oracle `CLOB` → PostgreSQL `TEXT` (필요시)

### 문자 인코딩

ETL 코드에는 Oracle ASCII7 → PostgreSQL UTF-8 변환 로직이 포함되어 있습니다:

```python
# 연결 시 UTF-8 인코딩 설정
connection = oracledb.connect(
    ...,
    encoding="UTF-8",
    nencoding="UTF-8"
)

# NLS 세션 설정
cursor.execute("ALTER SESSION SET NLS_LANGUAGE='KOREAN'")
cursor.execute("ALTER SESSION SET NLS_CHARACTERSET='AL32UTF8'")
```

### 성능 최적화

- BATCH_SIZE: 1000 (변경 불필요)
- Full Reload 전략: TRUNCATE + INSERT (변경 없음)
- 인덱스: pk_key, notiyy, name (생성 완료)

## 문의 사항

문제 발생 시 다음 로그를 확인하세요:

```bash
# Airflow 웹서버 로그
docker logs airflow-webserver

# Airflow 스케줄러 로그
docker logs airflow-scheduler

# PostgreSQL 로그 (테이블 생성 확인)
docker logs postgres-container

# Oracle 연결 테스트
docker exec -it airflow-webserver python3 -c "
import oracledb
conn = oracledb.connect(user='IF_IC0_TEMP_USER', password='eykk1275#',
                        host='10.253.41.194', port=1521, service_name='RECU')
cur = conn.cursor()
cur.execute('SELECT COUNT(*) FROM SREC.APPLICANT_INFO_TEMP')
print(f'Row count: {cur.fetchone()[0]}')
conn.close()
"
```
