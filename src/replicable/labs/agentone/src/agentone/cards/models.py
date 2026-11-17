"""Pydantic models: the data contracts of the app. Structured LLM outputs are validated against these."""
import uuid
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, Field, field_validator

def _now() -> datetime: return datetime.now(timezone.utc)
def _id() -> str: return uuid.uuid4().hex[:8]

Mode = Literal["study", "exercise"]
Intent = Literal["ask", "create_card", "submit_answer"]

class Triple(BaseModel):
    subject: str
    relation: str
    object: str
    @field_validator("subject", "relation", "object")
    @classmethod
    def _clean(cls, v: str) -> str:
        v = " ".join(v.split())
        if not v: raise ValueError("empty triple part")
        return v

class CardExtraction(BaseModel):
    """LLM output: knowledge-graph triples for one card."""
    triples: list[Triple] = Field(description="Short entity-relation-entity facts stated by the card. 2-6 triples.")

class DraftCard(BaseModel):
    """LLM output: a new flashcard drafted during a study session."""
    question: str
    answer: str

class Card(BaseModel):
    id: str = Field(default_factory=_id)
    question: str
    answer: str
    prerequisite_of: str | None = None   # set when created mid-study to support another card
    created_at: datetime = Field(default_factory=_now)

class RouteDecision(BaseModel):
    """LLM output: what the learner's message is for."""
    intent: Intent
    reason: str = ""

class Score(BaseModel):
    """LLM-judge output. Field bounds make an out-of-range judge reply a ValidationError (-> retry)."""
    score: float = Field(ge=0, le=1)
    verdict: Literal["correct", "partial", "incorrect"]
    feedback: str

class Attempt(BaseModel):
    card_id: str
    user_answer: str
    score: float
    verdict: str
    feedback: str
    at: datetime = Field(default_factory=_now)
