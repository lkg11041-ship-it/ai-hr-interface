from fastapi import APIRouter, HTTPException
import sys
sys.path.append('/app')
from scripts.bootstrap_search import main as bootstrap_main

router = APIRouter()

@router.post("/bootstrap")
def bootstrap():
    try:
        bootstrap_main()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(500, str(e))
