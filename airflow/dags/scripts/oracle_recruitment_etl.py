"""
Oracle to PostgreSQL ETL Script for APPLICANT_INFO table
Strategy: Full Reload (Truncate & Load)
Features: Logging, Error handling, Data retention policy (3 years)
Source: rsaiif.applicant_info (Oracle 11g)
Target: rsaiif.applicant_info (PostgreSQL)

Oracle 11g 연결:
- Thick Mode 사용 (Oracle Instant Client 21.13)
- Thin mode는 Oracle 12.1+ 만 지원하므로 Thick mode 필수
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import oracledb
import psycopg2
from psycopg2.extras import execute_batch

# ============================================================================
# Oracle Thick Mode 초기화 (Oracle 11g 지원)
# ============================================================================
try:
    # Thick mode 초기화 - Oracle Instant Client 사용
    # lib_dir: Docker 이미지 내부의 Oracle Instant Client 경로
    oracledb.init_oracle_client(lib_dir="/opt/oracle/instantclient")
    print("[INFO] Oracle Thick Mode initialized successfully")
    print("[INFO] Oracle Instant Client location: /opt/oracle/instantclient")
    print("[INFO] This enables Oracle 11g connectivity")
except Exception as e:
    # 이미 초기화되었거나 Instant Client를 찾을 수 없는 경우
    print(f"[WARN] Oracle Thick Mode initialization: {str(e)}")
    print("[WARN] Will attempt connection in Thin mode (may fail for Oracle 11g)...")
# ============================================================================

# Environment Variables
ORACLE_HOST = os.getenv("ORACLE_HOST")
ORACLE_PORT = os.getenv("ORACLE_PORT", "1521")
ORACLE_SERVICE = os.getenv("ORACLE_SERVICE", "RECU")
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")

PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Constants
DAG_ID = "etl_oracle_to_postgres_recruit_daily"
SOURCE_SCHEMA = "IF_IC0_TEMP_USER"
SOURCE_TABLE = "APPLICANT_INFO"
TARGET_SCHEMA = "rsaiif"
TARGET_TABLE = "applicant_info"
BATCH_SIZE = 1000

# Global state for sharing data between tasks
_extraction_data = {
    'rows': [],
    'row_count': 0,
    'run_id': None,
    'started_at': None,
}


def get_postgres_connection():
    """
    PostgreSQL 연결 생성

    연결 정보:
    - Host: 10.149.172.233
    - Database: rsaidb
    - User: rs_ai_user
    - 용도: Airflow 메타데이터 + ETL 타겟 DB
    """
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def get_oracle_connection():
    """
    Oracle 연결 생성 (Thick mode - Oracle 11g 지원)

    python-oracledb Thick mode 특징:
    - Oracle Instant Client 라이브러리 사용
    - Oracle 11g, 12c, 18c, 19c, 21c 모두 지원
    - Thin mode는 Oracle 12.1+ 만 지원하므로 11g는 Thick mode 필수

    연결 형식:
    - DSN: <host>:<port>/<service_name>
    - 예시: 10.253.41.194:1521/RECU (IF_IC0_TEMP_USER)

    주의사항:
    - Oracle Instant Client가 /opt/oracle/instantclient에 설치되어 있어야 함
    - SERVICE_NAME 또는 SID 사용 가능
    - 방화벽에서 Oracle 포트(1521) 허용 필요
    """
    print(f"[DEBUG] Connecting to Oracle (Thick Mode): {ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE}")
    print(f"[DEBUG] Oracle User: {ORACLE_USER}")

    # 방법 1: makedsn() 사용 (Oracle 11g와 가장 호환성 좋음)
    try:
        print("[DEBUG] Attempting connection method 1: makedsn() with SERVICE_NAME")
        dsn = oracledb.makedsn(
            host=ORACLE_HOST,
            port=ORACLE_PORT,
            service_name=ORACLE_SERVICE
        )
        print(f"[DEBUG] DSN created: {dsn}")

        connection = oracledb.connect(
            user=ORACLE_USER,
            password=ORACLE_PASSWORD,
            dsn=dsn,
            disable_oob=True,
            tcp_connect_timeout=60.0,
            retry_count=3,
            retry_delay=3,
            encoding="UTF-8",           # 클라이언트 인코딩: UTF-8
            nencoding="UTF-8"            # NCHAR 인코딩: UTF-8
        )

        # NLS 세션 파라미터 설정 (한글 처리)
        cursor = connection.cursor()
        cursor.execute("ALTER SESSION SET NLS_LANGUAGE='KOREAN'")
        cursor.execute("ALTER SESSION SET NLS_TERRITORY='KOREA'")
        cursor.execute("ALTER SESSION SET NLS_CHARACTERSET='AL32UTF8'")
        cursor.close()

        print(f"[DEBUG] Oracle connection successful (method 1)")
        print(f"[DEBUG] NLS settings: KOREAN/KOREA/AL32UTF8")
        return connection
    except Exception as e1:
        print(f"[WARN] Method 1 failed: {str(e1)}")

        # 방법 2: makedsn() with SID 사용 (일부 Oracle 11g는 SID만 지원)
        try:
            print("[DEBUG] Attempting connection method 2: makedsn() with SID")
            dsn = oracledb.makedsn(
                host=ORACLE_HOST,
                port=ORACLE_PORT,
                sid=ORACLE_SERVICE  # SERVICE_NAME 대신 SID로 시도
            )
            print(f"[DEBUG] DSN created: {dsn}")

            connection = oracledb.connect(
                user=ORACLE_USER,
                password=ORACLE_PASSWORD,
                dsn=dsn,
                disable_oob=True,
                tcp_connect_timeout=60.0,
                retry_count=3,
                retry_delay=3,
                encoding="UTF-8",
                nencoding="UTF-8"
            )

            # NLS 세션 파라미터 설정
            cursor = connection.cursor()
            cursor.execute("ALTER SESSION SET NLS_LANGUAGE='KOREAN'")
            cursor.execute("ALTER SESSION SET NLS_TERRITORY='KOREA'")
            cursor.execute("ALTER SESSION SET NLS_CHARACTERSET='AL32UTF8'")
            cursor.close()

            print(f"[DEBUG] Oracle connection successful (method 2 - SID)")
            print(f"[DEBUG] NLS settings: KOREAN/KOREA/AL32UTF8")
            return connection
        except Exception as e2:
            print(f"[WARN] Method 2 failed: {str(e2)}")

            # 방법 3: Easy Connect 문자열 (가장 단순한 방식)
            try:
                print("[DEBUG] Attempting connection method 3: Easy Connect String")
                dsn = f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE}"
                print(f"[DEBUG] DSN: {dsn}")

                connection = oracledb.connect(
                    user=ORACLE_USER,
                    password=ORACLE_PASSWORD,
                    dsn=dsn,
                    disable_oob=True,
                    tcp_connect_timeout=60.0,
                    encoding="UTF-8",
                    nencoding="UTF-8"
                )

                # NLS 세션 파라미터 설정
                cursor = connection.cursor()
                cursor.execute("ALTER SESSION SET NLS_LANGUAGE='KOREAN'")
                cursor.execute("ALTER SESSION SET NLS_TERRITORY='KOREA'")
                cursor.execute("ALTER SESSION SET NLS_CHARACTERSET='AL32UTF8'")
                cursor.close()

                print(f"[DEBUG] Oracle connection successful (method 3)")
                print(f"[DEBUG] NLS settings: KOREAN/KOREA/AL32UTF8")
                return connection
            except Exception as e3:
                print(f"[ERROR] All connection methods failed")
                print(f"  Method 1 (SERVICE_NAME): {str(e1)}")
                print(f"  Method 2 (SID): {str(e2)}")
                print(f"  Method 3 (Easy Connect): {str(e3)}")
                print(f"\n[SOLUTION] Oracle 11g 연결 문제 해결 방법:")
                print(f"  1. Oracle 서버에서 SQLNET.ORA 수정:")
                print(f"     SQLNET.ENCRYPTION_SERVER=ACCEPTED")
                print(f"     SQLNET.CRYPTO_CHECKSUM_SERVER=ACCEPTED")
                print(f"  2. Oracle 리스너 재시작: lsnrctl stop && lsnrctl start")
                print(f"  3. 서비스명 확인: SELECT VALUE FROM V$PARAMETER WHERE NAME='service_names';")
                print(f"  4. .env 파일에서 ORACLE_SERVICE를 SID로 변경 시도")
                raise e1  # 첫 번째 에러를 raise


def log_run_start():
    """ETL 시작 로그 기록"""
    print(f"[{datetime.now()}] Starting ETL run: {DAG_ID}")

    if not all([ORACLE_HOST, ORACLE_USER, ORACLE_PASSWORD, PG_HOST, PG_USER, PG_PASSWORD, PG_DB]):
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
                f"{SOURCE_SCHEMA}.{SOURCE_TABLE}",
                f"{TARGET_SCHEMA}.{TARGET_TABLE}",
                'IN_PROGRESS',
                _extraction_data['started_at']
            ))
            _extraction_data['run_id'] = cur.fetchone()[0]
            conn.commit()

    print(f"Run ID: {_extraction_data['run_id']}")
    return _extraction_data['run_id']


def extract_from_oracle():
    """
    Oracle에서 전체 데이터 건수 확인 (연결 테스트)

    Airflow에서는 task 간 메모리 공유가 불가능하므로,
    extract 단계에서는 건수만 확인하고,
    load 단계에서 Oracle에서 직접 읽어서 PostgreSQL에 적재합니다.
    """
    print(f"[{datetime.now()}] Checking Oracle connection and row count: {SOURCE_SCHEMA}.{SOURCE_TABLE}")

    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cur:
                # 건수만 확인
                count_sql = f"SELECT COUNT(*) FROM {SOURCE_SCHEMA}.{SOURCE_TABLE}"
                print(f"Executing: {count_sql}")
                cur.execute(count_sql)
                row_count = cur.fetchone()[0]

                print(f"Oracle table has {row_count} rows")

                # 전역 변수 업데이트 (로컬 테스트용)
                _extraction_data['row_count'] = row_count

                return row_count

    except Exception as e:
        log_error('extract_all', 'EXTRACT', e, f"{SOURCE_SCHEMA}.{SOURCE_TABLE}", None)
        raise


def load_to_production():
    """
    Oracle에서 데이터를 읽어 PostgreSQL 운영 테이블에 직접 적재 (TRUNCATE & INSERT)

    Airflow에서는 task 간 메모리가 공유되지 않으므로,
    이 함수에서 Oracle 연결을 다시 열어 데이터를 읽습니다.
    """
    print(f"[{datetime.now()}] Loading data from Oracle to PostgreSQL production table: {TARGET_SCHEMA}.{TARGET_TABLE}")

    try:
        # Step 1: Oracle에서 데이터 추출
        print(f"[{datetime.now()}] Extracting data from Oracle: {SOURCE_SCHEMA}.{SOURCE_TABLE}")
        with get_oracle_connection() as oracle_conn:
            with oracle_conn.cursor() as oracle_cur:
                # 전체 데이터 조회 (새 스키마: SREC.APPLICANT_INFO_TEMP - 155개 컬럼)
                select_sql = f"""
                    SELECT
                        PK_KEY, NOTIYY, BALNO, NOTINO, RESNO,
                        SCRCOMPCD, COMPANY_NM, NAME, JOB_NM, LOC_NM,
                        BIRDT, ADRESS, NATION, APPLY_PATH, BOHUN_YN,
                        BOHUN_RELATION, DISABLED_NM, DISABLED, HOBBY, HIGHSCHOOL,
                        HIGH_FLAG1, HIGH_FLAG2, HIGH_G_YM, HIGH_G_FLAG, HIGH_LOC,
                        JUNIOR_COLLEGE, JUNIOR_COLLEGE_FLAG1, JUNIOR_COLLEGE_FLAG2, JUNIOR_COLLEAGE_SPEC, JUNIOR_ENTER_YM,
                        JUNIOR_ENTER_FLAG, JUNIOR_G_YM, JUNIOR_G_FLAG, JUNIOR_LOC, UNIVERSITY,
                        UNIVERSITY_FLAG1, UNIVERSITY_FLAG2, UNIVERSITY_SPEC, UNIVERSITY_SPEC_SUB, UNIVERSITY_ENTER_YM,
                        UNIVERSITY_ENTER_FLAG, UNIVERSITY_G_YM, UNIVERSITY_G_FLAG, UNIVERSITY_LOC, GRA_SCHOOL,
                        GRA_SCHOOL_FLAG1, GRA_SCHOOL_FLAG2, GRA_SCHOOL_SPEC, GRA_SCHOOL_G_YM, GRA_SCHOOLY_G_FLAG,
                        GRA_SCHOOL_LOC, ARM_NM, ARM_STA_YMD, ARM_END_YMD, ARM_GUBUN,
                        ARM_RANKS, LANG1, LANG1_EX, LANG1_SCORE, LANG1_LV,
                        LANG1_JU, LANG2, LANG2_EX, LANG2_SCORE, LANG2_LV,
                        LANG2_JU, LANG3, LANG3_EX, LANG3_SCORE, LANG3_LV,
                        LANG3_JU, LANG4, LANG4_EX, LANG4_SCORE, LANG4_LV,
                        LANG4_JU, LICE1_NM, LICE1_GRADE, LICE1_JU, LICE2_NM,
                        LICE2_GRADE, LICE2_JU, LICE3_NM, LICE3_GRADE, LICE3_JU,
                        CAR_STA_YM_1, CAR_END_YM_1, CAR_NM_1, CAR_JIK_1, CAR_JOB_1,
                        CAR_RETIRE_1, CAR_STA_YM_2, CAR_END_YM_2, CAR_NM_2, CAR_JIK_2,
                        CAR_JOB_2, CAR_RETIRE_2, CAR_STA_YM_3, CAR_END_YM_3, CAR_NM_3,
                        CAR_JIK_3, CAR_JOB_3, CAR_RETIRE_3, CAR_STA_YM_4, CAR_END_YM_4,
                        CAR_NM_4, CAR_JIK_4, CAR_JOB_4, CAR_RETIRE_4, PRIZEORG_1,
                        PRIZECON_1, PRIZEDT_1, PRIZEORG_2, PRIZECON_2, PRIZEDT_2,
                        PRIZEORG_3, PRIZECON_3, PRIZEDT_3, PRIZEORG_4, PRIZECON_4,
                        PRIZEDT_4, SERVICE_NM_1, SERVICE_PERIOD_1, SERVICE_DETAIL_1, SERVICE_NM_2,
                        SERVICE_PERIOD_2, SERVICE_DETAIL_2, CLUB_NM_1, CLUB_PERIOD_1, CLUB_DETAIL_1,
                        CLUB_NM_2, CLUB_PERIOD_2, CLUB_DETAIL_2, CLUB_NM_3, CLUB_PERIOD_3,
                        CLUB_DETAIL_3, TRAIN_NM_1, TRAIN_PERIOD_1, TRAIN_DETAIL_1, TRAIN_NM_2,
                        TRAIN_PERIOD_2, TRAIN_DETAIL_2, TRAIN_NM_3, TRAIN_PERIOD_3, TRAIN_DETAIL_3,
                        TRIP_NM_1, TRIP_PERIOD_1, TRIP_DETAIL_1, TRIP_NM_2, TRIP_PERIOD_2,
                        TRIP_DETAIL_2, REASON, EXPERIENCE, SKILL
                    FROM {SOURCE_SCHEMA}.{SOURCE_TABLE}
                """
                print(f"Executing: SELECT * FROM {SOURCE_SCHEMA}.{SOURCE_TABLE}")
                oracle_cur.execute(select_sql)
                raw_rows = oracle_cur.fetchall()

                # Convert Oracle LOB objects and handle character encoding
                # Oracle: ASCII7 (US7ASCII) → PostgreSQL: UTF8
                rows = []
                conversion_errors = 0

                for row_idx, row in enumerate(raw_rows):
                    converted_row = []
                    for col_idx, value in enumerate(row):
                        try:
                            # Convert LOB (CLOB/BLOB) to string/bytes
                            if hasattr(value, 'read'):
                                lob_data = value.read()
                                # LOB 데이터 인코딩 변환
                                if isinstance(lob_data, bytes):
                                    # bytes → str (latin1로 디코드 후 UTF-8로 재인코딩)
                                    value = lob_data.decode('latin1', errors='replace')
                                else:
                                    value = lob_data

                            # 문자열 인코딩 변환 (Oracle ASCII7 → UTF-8)
                            if isinstance(value, str):
                                # 한글이 깨진 경우 복구 시도
                                # Oracle ASCII7에서 한글은 latin1로 잘못 인코딩되어 있을 수 있음
                                try:
                                    # 방법 1: 이미 UTF-8인 경우 그대로 사용
                                    value.encode('utf-8')
                                    converted_value = value
                                except UnicodeEncodeError:
                                    # 방법 2: latin1 → UTF-8 변환 시도
                                    try:
                                        converted_value = value.encode('latin1').decode('utf-8', errors='replace')
                                    except (UnicodeDecodeError, UnicodeEncodeError):
                                        # 방법 3: 변환 실패 시 원본 유지 (replace 모드로)
                                        converted_value = value
                                        conversion_errors += 1

                                converted_row.append(converted_value)

                            elif isinstance(value, bytes):
                                # bytes 타입은 UTF-8로 디코드
                                try:
                                    # 방법 1: UTF-8 디코드 시도
                                    converted_value = value.decode('utf-8', errors='ignore')
                                except UnicodeDecodeError:
                                    # 방법 2: latin1 → UTF-8 변환
                                    try:
                                        converted_value = value.decode('latin1', errors='replace')
                                    except UnicodeDecodeError:
                                        # 방법 3: ASCII로 대체
                                        converted_value = value.decode('ascii', errors='replace')
                                        conversion_errors += 1

                                converted_row.append(converted_value)

                            else:
                                # 숫자, 날짜 등 다른 타입은 그대로 유지
                                converted_row.append(value)

                        except Exception as e:
                            # 변환 중 예외 발생 시 None으로 대체
                            print(f"[WARN] Encoding conversion error at row {row_idx}, col {col_idx}: {str(e)}")
                            converted_row.append(None)
                            conversion_errors += 1

                    rows.append(tuple(converted_row))

                print(f"Extracted {len(rows)} rows from Oracle")
                if conversion_errors > 0:
                    print(f"[WARN] Character encoding conversion errors: {conversion_errors} values")

        if not rows:
            print("No data to load")
            return 0

        # Step 2: PostgreSQL에 적재
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # 트랜잭션 시작
                cur.execute("BEGIN")

                # 운영 테이블 초기화
                cur.execute(f"TRUNCATE TABLE {TARGET_SCHEMA}.{TARGET_TABLE}")
                print(f"Truncated production table: {TARGET_SCHEMA}.{TARGET_TABLE}")

                # 데이터 적재 (rsaiif.applicant_info의 모든 컬럼 - 155개)
                insert_sql = f"""
                    INSERT INTO {TARGET_SCHEMA}.{TARGET_TABLE}
                    (
                        PK_KEY, NOTIYY, BALNO, NOTINO, RESNO,
                        SCRCOMPCD, COMPANY_NM, NAME, JOB_NM, LOC_NM,
                        BIRDT, ADRESS, NATION, APPLY_PATH, BOHUN_YN,
                        BOHUN_RELATION, DISABLED_NM, DISABLED, HOBBY, HIGHSCHOOL,
                        HIGH_FLAG1, HIGH_FLAG2, HIGH_G_YM, HIGH_G_FLAG, HIGH_LOC,
                        JUNIOR_COLLEGE, JUNIOR_COLLEGE_FLAG1, JUNIOR_COLLEGE_FLAG2, JUNIOR_COLLEAGE_SPEC, JUNIOR_ENTER_YM,
                        JUNIOR_ENTER_FLAG, JUNIOR_G_YM, JUNIOR_G_FLAG, JUNIOR_LOC, UNIVERSITY,
                        UNIVERSITY_FLAG1, UNIVERSITY_FLAG2, UNIVERSITY_SPEC, UNIVERSITY_SPEC_SUB, UNIVERSITY_ENTER_YM,
                        UNIVERSITY_ENTER_FLAG, UNIVERSITY_G_YM, UNIVERSITY_G_FLAG, UNIVERSITY_LOC, GRA_SCHOOL,
                        GRA_SCHOOL_FLAG1, GRA_SCHOOL_FLAG2, GRA_SCHOOL_SPEC, GRA_SCHOOL_G_YM, GRA_SCHOOLY_G_FLAG,
                        GRA_SCHOOL_LOC, ARM_NM, ARM_STA_YMD, ARM_END_YMD, ARM_GUBUN,
                        ARM_RANKS, LANG1, LANG1_EX, LANG1_SCORE, LANG1_LV,
                        LANG1_JU, LANG2, LANG2_EX, LANG2_SCORE, LANG2_LV,
                        LANG2_JU, LANG3, LANG3_EX, LANG3_SCORE, LANG3_LV,
                        LANG3_JU, LANG4, LANG4_EX, LANG4_SCORE, LANG4_LV,
                        LANG4_JU, LICE1_NM, LICE1_GRADE, LICE1_JU, LICE2_NM,
                        LICE2_GRADE, LICE2_JU, LICE3_NM, LICE3_GRADE, LICE3_JU,
                        CAR_STA_YM_1, CAR_END_YM_1, CAR_NM_1, CAR_JIK_1, CAR_JOB_1,
                        CAR_RETIRE_1, CAR_STA_YM_2, CAR_END_YM_2, CAR_NM_2, CAR_JIK_2,
                        CAR_JOB_2, CAR_RETIRE_2, CAR_STA_YM_3, CAR_END_YM_3, CAR_NM_3,
                        CAR_JIK_3, CAR_JOB_3, CAR_RETIRE_3, CAR_STA_YM_4, CAR_END_YM_4,
                        CAR_NM_4, CAR_JIK_4, CAR_JOB_4, CAR_RETIRE_4, PRIZEORG_1,
                        PRIZECON_1, PRIZEDT_1, PRIZEORG_2, PRIZECON_2, PRIZEDT_2,
                        PRIZEORG_3, PRIZECON_3, PRIZEDT_3, PRIZEORG_4, PRIZECON_4,
                        PRIZEDT_4, SERVICE_NM_1, SERVICE_PERIOD_1, SERVICE_DETAIL_1, SERVICE_NM_2,
                        SERVICE_PERIOD_2, SERVICE_DETAIL_2, CLUB_NM_1, CLUB_PERIOD_1, CLUB_DETAIL_1,
                        CLUB_NM_2, CLUB_PERIOD_2, CLUB_DETAIL_2, CLUB_NM_3, CLUB_PERIOD_3,
                        CLUB_DETAIL_3, TRAIN_NM_1, TRAIN_PERIOD_1, TRAIN_DETAIL_1, TRAIN_NM_2,
                        TRAIN_PERIOD_2, TRAIN_DETAIL_2, TRAIN_NM_3, TRAIN_PERIOD_3, TRAIN_DETAIL_3,
                        TRIP_NM_1, TRIP_PERIOD_1, TRIP_DETAIL_1, TRIP_NM_2, TRIP_PERIOD_2,
                        TRIP_DETAIL_2, REASON, EXPERIENCE, SKILL
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """

                print(f"Inserting {len(rows)} rows into production table...")
                execute_batch(cur, insert_sql, rows, page_size=BATCH_SIZE)

                # 건수 확인
                cur.execute(f"SELECT COUNT(*) FROM {TARGET_SCHEMA}.{TARGET_TABLE}")
                final_count = cur.fetchone()[0]

                # 커밋
                cur.execute("COMMIT")

                print(f"Successfully loaded {final_count} rows to production table")
                return final_count

    except Exception as e:
        log_error('load_production', 'LOAD', e, f"{SOURCE_SCHEMA}.{SOURCE_TABLE}", f"{TARGET_SCHEMA}.{TARGET_TABLE}")
        raise


def log_run_success():
    """
    ETL 성공 로그 기록

    Airflow에서는 task 간 메모리가 공유되지 않으므로,
    run_history 테이블에서 최신 IN_PROGRESS 상태의 run을 찾아 업데이트합니다.
    """
    print(f"[{datetime.now()}] Logging ETL success")

    finished_at = datetime.now()

    with get_postgres_connection() as conn:
        with conn.cursor() as cur:
            # 최신 IN_PROGRESS 상태의 run_id와 시작 시간 조회
            cur.execute(f"""
                SELECT run_id, started_at
                FROM {TARGET_SCHEMA}.run_history
                WHERE dag_id = %s AND status = 'IN_PROGRESS'
                ORDER BY run_id DESC
                LIMIT 1
            """, (DAG_ID,))

            result = cur.fetchone()
            if not result:
                print("[WARN] No IN_PROGRESS run found to update")
                return

            run_id, started_at = result
            duration_ms = int((finished_at - started_at).total_seconds() * 1000)

            # 운영 테이블의 row count 조회
            cur.execute(f"SELECT COUNT(*) FROM {TARGET_SCHEMA}.{TARGET_TABLE}")
            row_count = cur.fetchone()[0]

            # 성공 상태로 업데이트
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
                row_count,
                row_count,
                finished_at,
                duration_ms,
                f"Successfully processed {row_count} rows",
                run_id
            ))
            conn.commit()

    print(f"ETL completed successfully. Run ID: {run_id}, Duration: {duration_ms}ms, Rows: {row_count}")


def log_run_failure():
    """
    ETL 실패 로그 기록

    Airflow에서는 task 간 메모리가 공유되지 않으므로,
    run_history 테이블에서 최신 IN_PROGRESS 상태의 run을 찾아 업데이트합니다.
    """
    print(f"[{datetime.now()}] Logging ETL failure")

    finished_at = datetime.now()

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # 최신 IN_PROGRESS 상태의 run_id와 시작 시간 조회
                cur.execute(f"""
                    SELECT run_id, started_at
                    FROM {TARGET_SCHEMA}.run_history
                    WHERE dag_id = %s AND status = 'IN_PROGRESS'
                    ORDER BY run_id DESC
                    LIMIT 1
                """, (DAG_ID,))

                result = cur.fetchone()
                if not result:
                    print("[WARN] No IN_PROGRESS run found to update")
                    return

                run_id, started_at = result
                duration_ms = int((finished_at - started_at).total_seconds() * 1000)

                # 실패 상태로 업데이트
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
                    run_id
                ))
                conn.commit()
                print(f"ETL failure logged. Run ID: {run_id}")
    except Exception as e:
        print(f"Error logging failure: {str(e)}")


def log_error(task_id: str, step: str, error: Exception, source_table: Optional[str], target_table: Optional[str]):
    """
    에러 로그 적재

    Airflow에서는 task 간 메모리가 공유되지 않으므로,
    run_history 테이블에서 최신 IN_PROGRESS 상태의 run_id를 조회하여 사용합니다.
    """
    error_message = str(error)
    error_class = type(error).__name__
    stack_trace = traceback.format_exc()

    print(f"ERROR in {task_id}/{step}: {error_message}")
    print(stack_trace)

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # 최신 IN_PROGRESS 상태의 run_id 조회
                cur.execute(f"""
                    SELECT run_id
                    FROM {TARGET_SCHEMA}.run_history
                    WHERE dag_id = %s AND status = 'IN_PROGRESS'
                    ORDER BY run_id DESC
                    LIMIT 1
                """, (DAG_ID,))

                result = cur.fetchone()
                run_id = result[0] if result else None

                # 에러 로그 삽입
                cur.execute(f"""
                    INSERT INTO {TARGET_SCHEMA}.error_log
                    (run_id, dag_id, task_id, step, error_class, error_message,
                     stacktrace, source_table, target_table, error_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    run_id,
                    DAG_ID,
                    task_id,
                    step,
                    error_class,
                    error_message[:500],  # 메시지 길이 제한
                    stack_trace[:2000],   # 스택트레이스 길이 제한
                    source_table,
                    target_table,
                    datetime.now()
                ))
                conn.commit()
                print(f"Error logged to error_log table (run_id: {run_id})")
    except Exception as log_err:
        print(f"Failed to log error: {str(log_err)}")


if __name__ == "__main__":
    # 로컬 테스트용
    try:
        log_run_start()
        extract_from_oracle()
        load_to_production()
        log_run_success()
        print("ETL completed successfully")
    except Exception as e:
        log_run_failure()
        print(f"ETL failed: {str(e)}")
        sys.exit(1)
