"""
FastAPI route tanımları.
"""
import io
import time
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from loguru import logger

from api.models import (
    AnalyzeFrameRequest,
    EventEntry,
    HealthResponse,
    QueryRequest,
    QueryResponse,
    StatsResponse,
)
from config import settings
from rag_engine.rag_query import RAGQueryEngine
from rag_engine.vector_store import VectorStore
from video_analyzer.detector import VideoDetector
from video_analyzer.event_logger import EventLogger

router = APIRouter()

# ── Bağımlılıklar (uygulama başlangıcında bir kez oluşturulur) ──────────────
_vector_store = VectorStore()
_rag_engine = RAGQueryEngine(vector_store=_vector_store)
_detector = VideoDetector()
_event_logger = EventLogger()

VERSION = "1.0.0"


# ── Sağlık ──────────────────────────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    return HealthResponse(status="ok", version=VERSION)


# ── İstatistikler ────────────────────────────────────────────────────────────

@router.get("/stats", response_model=StatsResponse, tags=["System"])
async def stats():
    return StatsResponse(
        total_events=_vector_store.total_events,
        model=settings.llm_model,
        grpc_address=f"{settings.grpc_host}:{settings.grpc_port}",
    )


# ── RAG Sorgu ────────────────────────────────────────────────────────────────

@router.post("/query", response_model=QueryResponse, tags=["RAG"])
async def query_events(req: QueryRequest):
    """
    Kullanıcı sorusunu RAG mimarisiyle yanıtlar.

    Örnek: "Bugün kırmızı araçlı biri geldi mi?"
    """
    try:
        result = _rag_engine.query(
            question=req.question,
            top_k=req.top_k,
            min_score=req.min_score,
        )
        return QueryResponse(
            answer=result["answer"],
            retrieved_events=result["retrieved_events"],
            usage=result["usage"],
            total_events_indexed=_vector_store.total_events,
        )
    except Exception as exc:
        logger.error(f"Sorgu hatası: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Görüntü Analizi ──────────────────────────────────────────────────────────

@router.post("/analyze/frame", tags=["Analysis"])
async def analyze_frame(
    file: UploadFile = File(..., description="JPEG/PNG kamera karesi"),
    source_id: str = "api",
):
    """
    Yüklenen görüntüyü YOLO ile analiz eder ve olayı kaydeder.
    """
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Sadece görüntü dosyaları kabul edilir")

    image_bytes = await file.read()
    try:
        result = _detector.analyze_frame_bytes(
            image_bytes=image_bytes,
            source_id=source_id,
            timestamp=int(time.time() * 1000),
        )
        # Tespit varsa VectorStore'a ekle
        if result.event_description:
            _vector_store.add_event(
                event_text=result.event_description,
                metadata={
                    "frame_id": result.frame_id,
                    "timestamp": result.timestamp,
                    "frame_path": result.frame_path,
                    "source_id": source_id,
                },
            )
        return {
            "frame_id": result.frame_id,
            "timestamp": result.timestamp,
            "event_description": result.event_description,
            "detections": [
                {
                    "label": d.label,
                    "confidence": round(d.confidence, 3),
                    "color_hint": d.color_hint,
                    "bbox": {"x1": d.bbox.x1, "y1": d.bbox.y1, "x2": d.bbox.x2, "y2": d.bbox.y2},
                }
                for d in result.detections
            ],
            "frame_path": result.frame_path,
        }
    except Exception as exc:
        logger.error(f"Frame analiz hatası: {exc}")
        raise HTTPException(status_code=500, detail=str(exc))


# ── Frame indirme ────────────────────────────────────────────────────────────

@router.get("/frames/{frame_name}", tags=["Analysis"])
async def get_frame(frame_name: str):
    """Annotate edilmiş kamera karesini indir."""
    path = Path(settings.frames_dir) / frame_name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Kare bulunamadı")
    return FileResponse(str(path), media_type="image/jpeg")


# ── Tüm olayları listele ─────────────────────────────────────────────────────

@router.get("/events", tags=["Events"])
async def list_events(limit: int = 50, offset: int = 0):
    """VectorStore'daki tüm olayları listeler."""
    all_events = _vector_store.get_all_events()
    total = len(all_events)
    page = all_events[offset : offset + limit]
    return {"total": total, "offset": offset, "limit": limit, "events": page}


# ── Olayları sıfırla ─────────────────────────────────────────────────────────

@router.delete("/events", tags=["Events"])
async def reset_events():
    """Tüm olay kayıtlarını siler (dikkatli kullanın)."""
    _vector_store.reset()
    return {"message": "Tüm olaylar silindi"}


# ── Olayları JSONL'den yeniden indeksle ──────────────────────────────────────

@router.post("/events/reindex", tags=["Events"])
async def reindex_events():
    """EventLogger JSONL dosyalarından VectorStore'u yeniden oluşturur."""
    count = _rag_engine.index_events_from_logger(_event_logger)
    return {"indexed": count, "total": _vector_store.total_events}
