"""
OpenSearch에서 PostgreSQL로 구조화된 데이터 마이그레이션
"""
import os
import psycopg2
from opensearchpy import OpenSearch

# OpenSearch 연결
os_client = OpenSearch(hosts=[os.getenv("OPENSEARCH_URL", "http://localhost:9200")])

# PostgreSQL 연결
pg_conn = psycopg2.connect(
    host=os.getenv("POSTGRES_HOST", "localhost"),
    port=os.getenv("POSTGRES_PORT", "5432"),
    database=os.getenv("POSTGRES_DB", "recruit"),
    user=os.getenv("POSTGRES_USER", "app"),
    password=os.getenv("POSTGRES_PASSWORD", "app_pw")
)
pg_cursor = pg_conn.cursor()

# OpenSearch에서 모든 후보자 데이터 가져오기
response = os_client.search(
    index="candidates",
    body={"query": {"match_all": {}}, "size": 1000},
    _source_includes=["applicant_id", "name", "age", "gender", "education", "experience_years", "skills", "industries"]
)

print(f"Found {response['hits']['total']['value']} candidates in OpenSearch")

# PostgreSQL에 데이터 삽입
inserted_count = 0
for hit in response['hits']['hits']:
    source = hit['_source']

    try:
        pg_cursor.execute("""
            INSERT INTO candidates (applicant_id, name, age, gender, education, experience_years, skills, industries)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (applicant_id) DO UPDATE SET
                name = EXCLUDED.name,
                age = EXCLUDED.age,
                gender = EXCLUDED.gender,
                education = EXCLUDED.education,
                experience_years = EXCLUDED.experience_years,
                skills = EXCLUDED.skills,
                industries = EXCLUDED.industries,
                updated_at = CURRENT_TIMESTAMP
        """, (
            source['applicant_id'],
            source['name'],
            source.get('age'),
            source.get('gender'),
            source.get('education'),
            source.get('experience_years'),
            source.get('skills', []),
            source.get('industries', [])
        ))
        inserted_count += 1
    except Exception as e:
        print(f"Error inserting {source['applicant_id']}: {e}")
        continue

pg_conn.commit()
print(f"Successfully migrated {inserted_count} candidates to PostgreSQL")

pg_cursor.close()
pg_conn.close()