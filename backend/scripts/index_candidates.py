import os
from sqlalchemy import text
from opensearchpy import OpenSearch
from ..db import engine
from ..services.embedder import embed_texts

OS = os.getenv("OPENSEARCH_URL","http://localhost:9200")
INDEX = os.getenv("OS_CAND_INDEX","candidates")
client = OpenSearch(hosts=[OS])

SQL = '''
SELECT a.applicant_id, coalesce(e.description,'') as passage
FROM hr.applicant a
LEFT JOIN hr.experience e ON a.applicant_id = e.applicant_id
LIMIT 100;
'''

def main():
    with engine.begin() as conn:
        rows = list(conn.execute(text(SQL)))
        texts = [r.passage or "" for r in rows]
        vecs = embed_texts(texts)
        for (r), v in zip(rows, vecs):
            body = {
                "applicant_id": str(r.applicant_id),
                "passage_text": r.passage,
                "skills": [],
                "industries": [],
                "years": 0.0,
                "passage_embedding": v.tolist()
            }
            client.index(index=INDEX, body=body)
    print(f"Indexed {len(rows)} docs into {INDEX}")
