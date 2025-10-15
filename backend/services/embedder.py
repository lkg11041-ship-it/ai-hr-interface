import os, numpy as np

_model = None
_dim = int(os.getenv("EMBED_DIM","384"))

def _try_load_model():
    global _model
    if _model is not None: return _model
    try:
        from sentence_transformers import SentenceTransformer
        name = os.getenv("EMBED_MODEL","sentence-transformers/all-MiniLM-L6-v2")
        _model = SentenceTransformer(name)
    except Exception:
        _model = None
    return _model

def embed_texts(texts):
    mdl = _try_load_model()
    if mdl:
        vecs = mdl.encode(texts, normalize_embeddings=True)
        return np.asarray(vecs, dtype="float32")
    vecs = []
    for t in texts:
        rng = np.random.default_rng(abs(hash(t)) % (2**32))
        v = rng.standard_normal(_dim).astype("float32")
        v /= max(1e-6, np.linalg.norm(v))
        vecs.append(v)
    return np.stack(vecs, axis=0)

def embed_query(text: str):
    return embed_texts([text])[0].tolist()
