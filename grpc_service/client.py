"""
gRPC Video Analysis Client

Kamera veya video dosyasından kare okur, gRPC ile sunucuya gönderir.
"""
import io
import time
import uuid
from pathlib import Path
from typing import Iterator

import cv2
import grpc
from loguru import logger
from PIL import Image

try:
    import video_analysis_pb2 as pb2
    import video_analysis_pb2_grpc as pb2_grpc
except ImportError:
    import sys
    sys.path.insert(0, "grpc_service")
    import video_analysis_pb2 as pb2
    import video_analysis_pb2_grpc as pb2_grpc

from config import settings


def _encode_frame(frame) -> bytes:
    """OpenCV BGR frame → JPEG bytes."""
    success, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
    if not success:
        raise ValueError("JPEG kodlama başarısız")
    return buf.tobytes()


def _make_channel() -> grpc.Channel:
    return grpc.insecure_channel(
        f"{settings.grpc_host}:{settings.grpc_port}",
        options=[
            ("grpc.max_send_message_length", 50 * 1024 * 1024),
            ("grpc.max_receive_message_length", 50 * 1024 * 1024),
        ],
    )


class VideoAnalysisClient:

    def __init__(self, host: str | None = None, port: int | None = None):
        address = f"{host or settings.grpc_host}:{port or settings.grpc_port}"
        self._channel = grpc.insecure_channel(address)
        self._stub = pb2_grpc.VideoAnalysisServiceStub(self._channel)
        logger.info(f"gRPC istemci bağlandı: {address}")

    # ── Tek kare ────────────────────────────────────────────────────────────

    def analyze_frame(self, frame, source_id: str = "camera") -> pb2.AnalysisResult:
        request = pb2.VideoFrame(
            frame_id=str(uuid.uuid4()),
            image_data=_encode_frame(frame),
            timestamp=int(time.time() * 1000),
            source_id=source_id,
        )
        return self._stub.AnalyzeFrame(request)

    # ── Akış modu ───────────────────────────────────────────────────────────

    def stream_video(
        self,
        source: str | int = 0,
        interval: float | None = None,
    ) -> Iterator[pb2.AnalysisResult]:
        """
        Kamera veya video dosyasını okur, her `interval` saniyede bir kare gönderir.
        Sonuçları yield eder.
        """
        cap = cv2.VideoCapture(source if isinstance(source, int) else str(source))
        if not cap.isOpened():
            raise RuntimeError(f"Video kaynağı açılamadı: {source}")

        interval = interval or settings.frame_capture_interval
        source_id = str(source)
        last_send = 0.0

        def _frame_gen():
            nonlocal last_send
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                now = time.time()
                if now - last_send >= interval:
                    last_send = now
                    yield pb2.VideoFrame(
                        frame_id=str(uuid.uuid4()),
                        image_data=_encode_frame(frame),
                        timestamp=int(now * 1000),
                        source_id=source_id,
                    )
            cap.release()

        try:
            for result in self._stub.StreamAnalysis(_frame_gen()):
                yield result
        except grpc.RpcError as exc:
            logger.error(f"gRPC akış hatası: {exc}")
            raise

    # ── Sağlık ──────────────────────────────────────────────────────────────

    def health_check(self) -> bool:
        try:
            resp = self._stub.HealthCheck(pb2.HealthRequest())
            return resp.status == "OK"
        except grpc.RpcError:
            return False

    def close(self):
        self._channel.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
