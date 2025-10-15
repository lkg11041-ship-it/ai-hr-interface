import os, json, httpx
from typing import Type, Dict, Any
from pydantic import BaseModel, ValidationError

LLM8B_URL = os.getenv("LLM8B_URL","")
LLM70B_URL = os.getenv("LLM70B_URL","")
LLM8B_MODEL = os.getenv("LLM8B_MODEL","gpt-4o-mini")
LLM70B_MODEL = os.getenv("LLM70B_MODEL","gpt-4o")
LLM_API_KEY = os.getenv("LLM_API_KEY","")
HEADERS = {"Authorization": f"Bearer {LLM_API_KEY}"} if LLM_API_KEY else {}

async def _chat(url: str, model: str, system: str, user: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role":"system","content":system},
            {"role":"user","content":user}
        ],
        "temperature": 0.2
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(url, json=payload, headers=HEADERS)
        r.raise_for_status()
        data = r.json()
        try:
            return data["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(data)

async def ask_json(system: str, user: str, Schema: Type[BaseModel], allow_upgrade: bool=True) -> Dict[str, Any]:
    last_err = None
    pairs = [(LLM8B_URL, LLM8B_MODEL)]
    if allow_upgrade:
        pairs.append((LLM70B_URL, LLM70B_MODEL))
    for url, model in pairs:
        if not url:
            continue
        try:
            text = await _chat(url, model, system, user)
            s = text.strip()
            start = s.find("{")
            if start != -1:
                s = s[start:]
            obj = json.loads(s)
            return Schema.model_validate(obj).model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            last_err = e
            continue
        except Exception as e:
            last_err = e
            continue
    raise ValueError(f"LLM validation failed: {last_err}")
