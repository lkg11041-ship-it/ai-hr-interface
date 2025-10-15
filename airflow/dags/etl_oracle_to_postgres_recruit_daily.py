from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
import sys

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
}

with DAG(
    dag_id="etl_oracle_to_postgres_recruit_daily",
    default_args=default_args,
    description='Daily ETL: Oracle HR.RECRUITMENT -> PostgreSQL app.recruitment with full reload strategy',
    schedule_interval="30 2 * * *",  # 매일 02:30 실행
    start_date=datetime(2025, 10, 3),
    catchup=False,
    tags=["etl", "oracle", "postgres", "recruitment", "production"],
) as dag:

    # Task 1: 시작 로그 기록
    log_start = PythonOperator(
        task_id='log_start',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').log_run_start(),
    )

    # Task 2: Oracle에서 전체 데이터 추출
    extract_all = PythonOperator(
        task_id='extract_all',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').extract_from_oracle(),
    )

    # Task 3: Stage 테이블에 적재
    stage_load = PythonOperator(
        task_id='stage_load',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').load_to_stage(),
    )

    # Task 4: 원자적 교체 (TRUNCATE + INSERT)
    swap_replace = PythonOperator(
        task_id='swap_replace',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').swap_and_replace(),
    )

    # Task 5: 성공 로그 기록
    log_success = PythonOperator(
        task_id='log_success',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').log_run_success(),
    )

    # Task 6: 3년 초과 데이터 삭제 (보존정책)
    cleanup_3y = PythonOperator(
        task_id='cleanup_3y',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').cleanup_old_data(),
    )

    # Task 7: 종료
    end = BashOperator(
        task_id='end',
        bash_command='echo "ETL pipeline completed successfully"',
    )

    # Task 8: 실패 처리 (모든 실패 시 실행)
    log_failure = PythonOperator(
        task_id='log_failure',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').log_run_failure(),
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Task Flow
    log_start >> extract_all >> stage_load >> swap_replace >> log_success >> cleanup_3y >> end

    # 실패 시 에러 로그 적재
    [extract_all, stage_load, swap_replace] >> log_failure
