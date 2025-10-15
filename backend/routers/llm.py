import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from schemas import SummaryOut, TraitsOut, QuestionItem, DSL
from services.llm_client import ask_json

router = APIRouter()

class SummarizeIn(BaseModel):
    structured_fields: dict
    evidence_sentences: list

class TraitsIn(BaseModel):
    structured_json: dict
    trait_labels: list
    skill_vocab: list

class QuestionsIn(BaseModel):
    applicant_context: dict

class ParseDSLIn(BaseModel):
    natural_query: str
    skill_vocab: list
    role_vocab: list

@router.post("/summarize", response_model=SummaryOut)
async def summarize(payload: SummarizeIn):
    system = "너는 채용 요약 도우미. 숫자/기간/성과는 원문 근거 있을 때만. 120~300자. JSON만."
    user = json.dumps({"structured_fields": payload.structured_fields, "evidence": payload.evidence_sentences}, ensure_ascii=False)
    try:
        data = await ask_json(system, user, SummaryOut)
        return data
    except Exception as e:
        raise HTTPException(422, str(e))

@router.post("/traits", response_model=TraitsOut)
async def traits(payload: TraitsIn):
    system = "폐쇄 라벨/스킬 vocab만 사용. 각 항목 evidence 필수. JSON만."
    user = json.dumps({"input": payload.structured_json, "trait_labels": payload.trait_labels, "skill_vocab": payload.skill_vocab}, ensure_ascii=False)
    try:
        data = await ask_json(system, user, TraitsOut)
        return data
    except Exception as e:
        raise HTTPException(422, str(e))

@router.post("/questions", response_model=list[QuestionItem])
async def questions(payload: QuestionsIn):
    system = "지원자 특이점/리스크 기반 5~8개 질문 생성. intent/difficulty/evidence 포함. JSON만."
    user = json.dumps(payload.applicant_context, ensure_ascii=False)
    try:
        data = await ask_json(system, user, list[QuestionItem])  # type: ignore
        return data
    except Exception as e:
        raise HTTPException(422, str(e))

@router.post("/parse_dsl", response_model=DSL)
async def parse_dsl(payload: ParseDSLIn):
    system = "자연어→DSL(JSON). 금융권->[Banking,Securities,Card,Insurance], 10년차 이상→min_years=10."
    user = json.dumps({"q": payload.natural_query, "skills": payload.skill_vocab, "roles": payload.role_vocab}, ensure_ascii=False)
    try:
        data = await ask_json(system, user, DSL)
        return data
    except Exception as e:
        raise HTTPException(422, str(e))
