FROM apache/airflow:2.9.2-python3.11
USER root
RUN apt-get update && apt-get install -y build-essential default-libmysqlclient-dev curl && rm -rf /var/lib/apt/lists/*
USER airflow
RUN pip install --no-cache-dir \
    psycopg2-binary \
    pandas pandera pydantic \
    opensearch-py \
    httpx requests oracledb \
    sentence-transformers torch --extra-index-url https://download.pytorch.org/whl/cpu
