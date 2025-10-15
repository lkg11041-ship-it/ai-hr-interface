from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.trigger_rule import TriggerRule
import sys

default_args = {
    'owner': 'search',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
}

with DAG(
    dag_id="etl_postgres_to_opensearch_daily",
    default_args=default_args,
    description='Daily ETL: PostgreSQL recruitment data -> OpenSearch with vector embeddings',
    schedule_interval="0 4 * * *",  # 매일 04:00 실행 (Oracle ETL, dbt 이후)
    start_date=datetime(2025, 10, 6),
    catchup=False,
    tags=["etl", "opensearch", "embedding", "vector", "production"],
) as dag:

    # Task 1: 시작 로그 기록
    log_start = PythonOperator(
        task_id='log_start',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('postgres_to_opensearch_etl').log_run_start(),
    )

    # Task 2: PostgreSQL에서 데이터 추출
    extract_data = PythonOperator(
        task_id='extract_from_postgres',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('postgres_to_opensearch_etl').extract_from_postgres(),
    )

    # Task 3: 임베딩 생성 및 OpenSearch 인덱싱
    transform_index = PythonOperator(
        task_id='transform_and_index_to_opensearch',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('postgres_to_opensearch_etl').transform_and_index_to_opensearch(),
    )

    # Task 4: 성공 로그 기록
    log_success = PythonOperator(
        task_id='log_success',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('postgres_to_opensearch_etl').log_run_success(),
    )

    # Task 5: 종료
    end = BashOperator(
        task_id='end',
        bash_command='echo "Vector indexing pipeline completed successfully"',
    )

    # Task 6: 실패 처리
    log_failure = PythonOperator(
        task_id='log_failure',
        python_callable=lambda: __import__('sys').path.insert(0, '/opt/airflow/dags/scripts') or
                                __import__('postgres_to_opensearch_etl').log_run_failure(),
        trigger_rule=TriggerRule.ONE_FAILED,
    )

    # Task Flow
    log_start >> extract_data >> transform_index >> log_success >> end

    # 실패 시 에러 로그 적재
    [extract_data, transform_index] >> log_failure
