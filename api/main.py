"""
FastAPI uygulama giriş noktası.
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from loguru import logger

from api.routes import router
from config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API sunucusu başlatılıyor...")
    Path(settings.frames_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.events_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.faiss_index_path).parent.mkdir(parents=True, exist_ok=True)
    yield
    logger.info("API sunucusu kapatılıyor...")


app = FastAPI(
    title="Akıllı Video Analiz & RAG Asistanı",
    description=(
        "OpenCV + YOLO tabanlı video analizi ve FAISS + Claude RAG motoru. "
        "Güvenlik kamerası görüntülerini sorgulayın."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")

# Annotate edilmiş frame'leri statik olarak sun
frames_path = Path(settings.frames_dir)
frames_path.mkdir(parents=True, exist_ok=True)
app.mount("/frames", StaticFiles(directory=str(frames_path)), name="frames")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
    )
