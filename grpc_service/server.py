"""
gRPC Video Analysis Server

Video karelerini alır, YOLO ile analiz eder ve sonuçları döndürür.
RAG motoruna olayları kaydeder.
"""
import asyncio
import time
from concurrent import futures

import grpc
from loguru import logger

# Proto stub'ları (generate_proto.sh çalıştırıldıktan sonra oluşur)
try:
    import video_analysis_pb2 as pb2
    import video_analysis_pb2_grpc as pb2_grpc
except ImportError:
    import sys
    sys.path.insert(0, "grpc_service")
    import video_analysis_pb2 as pb2
    import video_analysis_pb2_grpc as pb2_grpc

from video_analyzer.detector import VideoDetector
from rag_engine.vector_store import VectorStore
from config import settings

VERSION = "1.0.0"


class VideoAnalysisServicer(pb2_grpc.VideoAnalysisServiceServicer):

    def __init__(self):
        self.detector = VideoDetector()
        self.vector_store = VectorStore()
        logger.info("VideoAnalysisServicer başlatıldı")

    # ── Tek kare ────────────────────────────────────────────────────────────

    def AnalyzeFrame(self, request: pb2.VideoFrame, context) -> pb2.AnalysisResult:
        try:
            result = self.detector.analyze_frame_bytes(
                frame_id=request.frame_id,
                image_bytes=request.image_data,
                timestamp=request.timestamp,
                source_id=request.source_id,
            )
            if result.event_description:
                self.vector_store.add_event(
                    event_text=result.event_description,
                    metadata={
                        "frame_id": result.frame_id,
                        "timestamp": result.timestamp,
                        "frame_path": result.frame_path,
                        "source_id": request.source_id,
                    },
                )
            return result
        except Exception as exc:
            logger.error(f"AnalyzeFrame hatası: {exc}")
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return pb2.AnalysisResult()

    # ── Toplu kare ──────────────────────────────────────────────────────────

    def AnalyzeBatch(
        self, request: pb2.BatchFrameRequest, context
    ) -> pb2.BatchAnalysisResponse:
        results, errors = [], 0
        for frame in request.frames:
            try:
                result = self.AnalyzeFrame(frame, context)
                results.append(result)
            except Exception:
                errors += 1
        return pb2.BatchAnalysisResponse(
            results=results,
            processed_count=len(results),
            error_count=errors,
        )

    # ── Çift yönlü akış ─────────────────────────────────────────────────────

    def StreamAnalysis(self, request_iterator, context):
        for frame in request_iterator:
            if context.is_active():
                result = self.AnalyzeFrame(frame, context)
                yield result
            else:
                break

    # ── Sağlık ──────────────────────────────────────────────────────────────

    def HealthCheck(self, request, context) -> pb2.HealthResponse:
        return pb2.HealthResponse(status="OK", version=VERSION)


# ── Sunucu başlatma ─────────────────────────────────────────────────────────

def serve():
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=10),
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )
    pb2_grpc.add_VideoAnalysisServiceServicer_to_server(
        VideoAnalysisServicer(), server
    )
    address = f"{settings.grpc_host}:{settings.grpc_port}"
    server.add_insecure_port(address)
    server.start()
    logger.info(f"gRPC sunucu dinliyor: {address}")
    try:
        server.wait_for_termination()
    except KeyboardInterrupt:
        server.stop(grace=5)
        logger.info("gRPC sunucu durduruldu")


if __name__ == "__main__":
    serve()
