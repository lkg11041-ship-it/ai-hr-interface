import os, json, time
from opensearchpy import OpenSearch

OS = os.getenv("OPENSEARCH_URL","http://localhost:9200")
client = OpenSearch(hosts=[OS])

def put_pipeline(name, path):
    with open(path, "r", encoding="utf-8") as f:
        body = json.load(f)
    client.transport.perform_request("PUT", f"/_search/pipeline/{name}", body=body)

def put_index(name, path):
    with open(path, "r", encoding="utf-8") as f:
        body = json.load(f)
    client.indices.create(index=name, body=body, ignore=400)

def main():
    print("Waiting OpenSearch...")
    for _ in range(60):
        try:
            client.cat.health()
            break
        except Exception:
            time.sleep(2)
    base = "/app/infra/opensearch"
    # Skip pipelines for now - OpenSearch 2.13 may not support score-ranker-processor
    # put_pipeline("rrf-pipeline", f"{base}/pipelines/rrf-pipeline.json")
    # put_pipeline("normalize-pipeline", f"{base}/pipelines/normalize-pipeline.json")
    put_index("candidates", f"{base}/mappings/candidates-index.json")
    print("Bootstrap completed.")

if __name__ == "__main__":
    main()
