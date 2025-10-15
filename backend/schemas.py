from pydantic import BaseModel, Field, confloat
from typing import List, Optional, Any, Dict

class Evidence(BaseModel):
    doc_id: int
    offset: Optional[List[int]] = None
    snippet: Optional[str] = None

class SummaryOut(BaseModel):
    summary: str = Field(max_length=400)
    evidence: List[Evidence]

class TraitItem(BaseModel):
    label: str
    confidence: confloat(ge=0, le=1)
    evidence: List[Evidence]

class SkillItem(BaseModel):
    name: str
    level: str
    years: Optional[float]
    evidence: List[Evidence]

class TraitsOut(BaseModel):
    traits: List[TraitItem]
    skills: List[SkillItem]
    certs: Optional[List[Dict[str, Any]]] = []

class QuestionItem(BaseModel):
    question: str
    intent: str
    difficulty: Optional[str] = None
    evidence: List[Evidence]

class DSL(BaseModel):
    filters: Dict[str, Any]
    sort: Optional[str] = "relevance"
    limit: Optional[int] = 20
    page: Optional[int] = 1
