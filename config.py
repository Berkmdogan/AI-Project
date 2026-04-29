from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path


class Settings(BaseSettings):
    # Anthropic
    anthropic_api_key: str = Field(..., env="ANTHROPIC_API_KEY")
    llm_model: str = Field("claude-sonnet-4-6", env="LLM_MODEL")
    embedding_model: str = Field("all-MiniLM-L6-v2", env="EMBEDDING_MODEL")

    # YOLO
    yolo_model: str = Field("yolov8n.pt", env="YOLO_MODEL")
    yolo_confidence: float = Field(0.5, env="YOLO_CONFIDENCE")

    # gRPC
    grpc_host: str = Field("0.0.0.0", env="GRPC_HOST")
    grpc_port: int = Field(50051, env="GRPC_PORT")

    # API
    api_host: str = Field("0.0.0.0", env="API_HOST")
    api_port: int = Field(8000, env="API_PORT")

    # Vector Store
    faiss_index_path: Path = Field("data/vector_store/events.index", env="FAISS_INDEX_PATH")
    events_metadata_path: Path = Field("data/vector_store/events_metadata.json", env="EVENTS_METADATA_PATH")

    # Video
    frame_capture_interval: float = Field(1.0, env="FRAME_CAPTURE_INTERVAL")
    video_source: str = Field("0", env="VIDEO_SOURCE")
    frames_dir: Path = Field("data/frames", env="FRAMES_DIR")
    events_dir: Path = Field("data/events", env="EVENTS_DIR")

    # RAG
    top_k_results: int = Field(5, env="TOP_K_RESULTS")
    min_similarity_score: float = Field(0.3, env="MIN_SIMILARITY_SCORE")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
