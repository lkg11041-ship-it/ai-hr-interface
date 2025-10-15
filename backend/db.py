import os
from sqlalchemy import create_engine

def get_engine():
    host = os.getenv("POSTGRES_HOST","localhost")
    port = os.getenv("POSTGRES_PORT","5432")
    db   = os.getenv("POSTGRES_DB","recruit")
    user = os.getenv("POSTGRES_USER","app")
    pw   = os.getenv("POSTGRES_PASSWORD","app_pw")
    url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
    return create_engine(url, future=True)

engine = get_engine()
