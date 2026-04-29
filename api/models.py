"""Pydantic request/response modelleri."""
from pydantic import BaseModel, Field
from typing import Any


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3, description="Kullanıcı sorusu")
    top_k: int = Field(5, ge=1, le=20, description="Döndürülecek maksimum olay sayısı")
    min_score: float = Field(0.3, ge=0.0, le=1.0, description="Minimum benzerlik skoru")
    stream: bool = Field(False, description="Yanıt akış modunda mı dönsün?")


class QueryResponse(BaseModel):
    answer: str
    retrieved_events: list[dict[str, Any]]
    usage: dict[str, Any]
    total_events_indexed: int


class AnalyzeFrameRequest(BaseModel):
    source_id: str = Field("api", description="Kamera/kaynak kimliği")


class EventEntry(BaseModel):
    text: str
    score: float
    timestamp: int | None = None
    frame_path: str | None = None


class StatsResponse(BaseModel):
    total_events: int
    model: str
    grpc_address: str


class HealthResponse(BaseModel):
    status: str
    version: str
