from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import llm, search, admin

app = FastAPI(title="Recruit AI Backend", version="0.2.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(llm.router, prefix="/llm", tags=["llm"])
app.include_router(search.router, prefix="/search", tags=["search"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])

@app.get("/healthz")
def health():
    return {"ok": True}
