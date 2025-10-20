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
ORACLE_SERVICE = os.getenv("ORACLE_SERVICE", "XEPDB1")
ORACLE_USER = os.getenv("ORACLE_USER")
ORACLE_PASSWORD = os.getenv("ORACLE_PASSWORD")

PG_HOST = os.getenv("POSTGRES_HOST")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
PG_DB = os.getenv("POSTGRES_DB")
PG_USER = os.getenv("POSTGRES_USER")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD")

# Constants
DAG_ID = "etl_oracle_to_postgres_recruit_daily"
SOURCE_SCHEMA = "rsaiif"
SOURCE_TABLE = "applicant_info"
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
    - 예시: 10.253.41.229:1521/RECU (IF_IC0_TEMP_USER)

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
            retry_delay=3
        )
        print(f"[DEBUG] Oracle connection successful (method 1)")
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
                retry_delay=3
            )
            print(f"[DEBUG] Oracle connection successful (method 2 - SID)")
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
                    tcp_connect_timeout=60.0
                )
                print(f"[DEBUG] Oracle connection successful (method 3)")
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
    """Oracle에서 전체 데이터 추출"""
    print(f"[{datetime.now()}] Extracting data from Oracle: {SOURCE_SCHEMA}.{SOURCE_TABLE}")

    try:
        with get_oracle_connection() as conn:
            with conn.cursor() as cur:
                # 전체 데이터 조회 (rsaiif.applicant_info의 모든 컬럼 - 149개)
                select_sql = f"""
                    SELECT
                        APPLICANT_INFO_ID, COMPANY_NM, NAME, JOB_NM, LOC_NM,
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
                cur.execute(select_sql)
                raw_rows = cur.fetchall()

                # Convert Oracle LOB objects to strings
                rows = []
                for row in raw_rows:
                    converted_row = []
                    for value in row:
                        # Convert LOB (CLOB/BLOB) to string/bytes
                        if hasattr(value, 'read'):
                            converted_row.append(value.read())
                        else:
                            converted_row.append(value)
                    rows.append(tuple(converted_row))

                _extraction_data['rows'] = rows
                _extraction_data['row_count'] = len(rows)

                print(f"Extracted {len(rows)} rows from Oracle")
                return len(rows)

    except Exception as e:
        log_error('extract_all', 'EXTRACT', e, f"{SOURCE_SCHEMA}.{SOURCE_TABLE}", None)
        raise


def load_to_production():
    """운영 테이블에 직접 데이터 적재 (TRUNCATE & INSERT)"""
    print(f"[{datetime.now()}] Loading data directly to production table: {TARGET_SCHEMA}.{TARGET_TABLE}")

    rows = _extraction_data['rows']
    if not rows:
        print("No data to load")
        return 0

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # 트랜잭션 시작
                cur.execute("BEGIN")

                # 운영 테이블 초기화
                cur.execute(f"TRUNCATE TABLE {TARGET_SCHEMA}.{TARGET_TABLE}")
                print(f"Truncated production table: {TARGET_SCHEMA}.{TARGET_TABLE}")

                # 데이터 적재 (rsaiif.applicant_info의 모든 컬럼 - 149개)
                insert_sql = f"""
                    INSERT INTO {TARGET_SCHEMA}.{TARGET_TABLE}
                    (
                        APPLICANT_INFO_ID, COMPANY_NM, NAME, JOB_NM, LOC_NM,
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
                        %s, %s, %s
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
                f"Successfully processed {_extraction_data['row_count']} rows",
                _extraction_data['run_id']
            ))
            conn.commit()

    print(f"ETL completed successfully. Duration: {duration_ms}ms")


def cleanup_old_data():
    """
    3년 초과 데이터 삭제 (보존정책)

    Note: rsaiif.applicant_info 테이블에는 load_date 컬럼이 없으므로 cleanup 건너뜀
    Full Reload 전략으로 매번 전체 데이터를 교체하므로 별도 cleanup 불필요
    """
    print(f"[{datetime.now()}] Data cleanup check")
    print(f"Skipping cleanup - rsaiif.applicant_info uses Full Reload strategy")
    return 0


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


def log_error(task_id: str, step: str, error: Exception, source_table: Optional[str], target_table: Optional[str]):
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
                    error_message[:500],  # 메시지 길이 제한
                    stack_trace[:2000],   # 스택트레이스 길이 제한
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
        extract_from_oracle()
        load_to_production()
        log_run_success()
        cleanup_old_data()
        print("ETL completed successfully")
    except Exception as e:
        log_run_failure()
        print(f"ETL failed: {str(e)}")
        sys.exit(1)
