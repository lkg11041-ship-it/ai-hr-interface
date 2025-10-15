"""
Oracle to PostgreSQL ETL Script for APPLICANT_INFO table
Strategy: Full Reload (Truncate & Load)
Features: Logging, Error handling, Data retention policy (3 years)
Source: app.applicant_info (Oracle)
Target: app.applicant_info (PostgreSQL)
"""

import os
import sys
import traceback
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import oracledb
import psycopg2
from psycopg2.extras import execute_batch

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
SOURCE_SCHEMA = "app"
SOURCE_TABLE = "applicant_info"
TARGET_SCHEMA = "app"
TARGET_TABLE = "applicant_info"
STAGE_TABLE = "applicant_info_stage"
RETENTION_YEARS = 3
BATCH_SIZE = 1000

# Global state for sharing data between tasks
_extraction_data = {
    'rows': [],
    'row_count': 0,
    'run_id': None,
    'started_at': None,
}


def get_postgres_connection():
    """PostgreSQL 연결 생성"""
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )


def get_oracle_connection():
    """Oracle 연결 생성 (Thin mode - no Oracle Client required)"""
    dsn = f"{ORACLE_HOST}:{ORACLE_PORT}/{ORACLE_SERVICE}"
    # Thin mode: pure Python implementation, no Oracle Client needed
    return oracledb.connect(user=ORACLE_USER, password=ORACLE_PASSWORD, dsn=dsn)


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
                # 전체 데이터 조회 (app.applicant_info의 모든 컬럼)
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


def load_to_stage():
    """Stage 테이블에 데이터 적재"""
    print(f"[{datetime.now()}] Loading data to stage table: {TARGET_SCHEMA}.{STAGE_TABLE}")

    rows = _extraction_data['rows']
    if not rows:
        print("No data to load")
        return 0

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # Stage 테이블 초기화
                cur.execute(f"TRUNCATE TABLE {TARGET_SCHEMA}.{STAGE_TABLE}")
                print(f"Truncated stage table: {TARGET_SCHEMA}.{STAGE_TABLE}")

                # 데이터 적재 (app.applicant_info의 모든 컬럼)
                insert_sql = f"""
                    INSERT INTO {TARGET_SCHEMA}.{STAGE_TABLE}
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

                print(f"Inserting {len(rows)} rows into stage table...")
                execute_batch(cur, insert_sql, rows, page_size=BATCH_SIZE)
                conn.commit()

                print(f"Successfully loaded {len(rows)} rows to stage")
                return len(rows)

    except Exception as e:
        log_error('stage_load', 'LOAD', e, f"{SOURCE_SCHEMA}.{SOURCE_TABLE}", f"{TARGET_SCHEMA}.{STAGE_TABLE}")
        raise


def swap_and_replace():
    """원자적 교체: Stage -> Production 테이블"""
    print(f"[{datetime.now()}] Swapping stage to production table")

    try:
        with get_postgres_connection() as conn:
            with conn.cursor() as cur:
                # 트랜잭션으로 원자적 교체
                cur.execute(f"BEGIN")

                # Production 테이블 초기화
                cur.execute(f"TRUNCATE TABLE {TARGET_SCHEMA}.{TARGET_TABLE}")
                print(f"Truncated production table: {TARGET_SCHEMA}.{TARGET_TABLE}")

                # Stage에서 Production으로 데이터 복사
                cur.execute(f"""
                    INSERT INTO {TARGET_SCHEMA}.{TARGET_TABLE}
                    SELECT * FROM {TARGET_SCHEMA}.{STAGE_TABLE}
                """)

                # 건수 확인
                cur.execute(f"SELECT COUNT(*) FROM {TARGET_SCHEMA}.{TARGET_TABLE}")
                final_count = cur.fetchone()[0]

                cur.execute(f"COMMIT")

                print(f"Successfully swapped {final_count} rows to production table")
                return final_count

    except Exception as e:
        log_error('swap_replace', 'LOAD', e, f"{TARGET_SCHEMA}.{STAGE_TABLE}", f"{TARGET_SCHEMA}.{TARGET_TABLE}")
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
    """3년 초과 데이터 삭제 (보존정책)"""
    print(f"[{datetime.now()}] Cleaning up data older than {RETENTION_YEARS} years")

    # Note: applicant_info 테이블에는 load_date 컬럼이 없으므로 cleanup 건너뜀
    print(f"Skipping cleanup - applicant_info table has no load_date column")
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
        load_to_stage()
        swap_and_replace()
        log_run_success()
        cleanup_old_data()
        print("ETL completed successfully")
    except Exception as e:
        log_run_failure()
        print(f"ETL failed: {str(e)}")
        sys.exit(1)
