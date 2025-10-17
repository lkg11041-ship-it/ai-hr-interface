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
    description='Daily ETL: Oracle app.applicant_info -> PostgreSQL app.applicant_info with full reload strategy',
    schedule_interval="30 2 * * *",  # 매일 02:30 실행
    start_date=datetime(2025, 10, 3),
    catchup=False,
    tags=["etl", "oracle", "postgres", "applicant_info", "production"],
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

    # Task 3: 운영 테이블에 직접 적재 (TRUNCATE + INSERT)
    load_production = PythonOperator(
        task_id='load_production',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').load_to_production(),
    )

    # Task 4: 성공 로그 기록
    log_success = PythonOperator(
        task_id='log_success',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').log_run_success(),
    )

    # Task 5: 3년 초과 데이터 삭제 (보존정책 - 현재는 건너뜀)
    cleanup_3y = PythonOperator(
        task_id='cleanup_3y',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').cleanup_old_data(),
    )

    # Task 6: 종료
    end = BashOperator(
        task_id='end',
        bash_command='echo "ETL pipeline completed successfully"',
    )

    # Task 7: 실패 처리 (모든 실패 시 실행)
    log_failure = PythonOperator(
        task_id='log_failure',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('oracle_recruitment_etl').log_run_failure(),
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Task Flow (단순화: Stage 테이블 제거)
    log_start >> extract_all >> load_production >> log_success >> cleanup_3y >> end

    # 실패 시 에러 로그 적재
    [extract_all, load_production] >> log_failure
