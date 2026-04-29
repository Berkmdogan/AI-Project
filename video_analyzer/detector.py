"""
YOLO tabanlı nesne tespiti ve olay üretimi.

Her analiz edilen kare için:
  - Nesneleri tespit eder
  - Her nesnenin baskın rengini bulur
  - İnsan-okunur olay metni üretir ("09:15 - Kırmızı araç otoparka girdi")
  - Kareyi diske kaydeder
"""
import io
import time
import uuid
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
from loguru import logger
from PIL import Image
from ultralytics import YOLO

from config import settings
from video_analyzer.color_detector import dominant_color
from video_analyzer.event_logger import EventLogger

try:
    import video_analysis_pb2 as pb2
except ImportError:
    import sys
    sys.path.insert(0, "grpc_service")
    import video_analysis_pb2 as pb2

# COCO sınıf adlarını Türkçeye çevirir
_LABEL_TR: dict[str, str] = {
    "person": "kişi",
    "car": "araç",
    "truck": "kamyon",
    "bus": "otobüs",
    "motorcycle": "motosiklet",
    "bicycle": "bisiklet",
    "dog": "köpek",
    "cat": "kedi",
    "backpack": "sırt çantası",
    "handbag": "el çantası",
    "suitcase": "bavul",
    "cell phone": "cep telefonu",
    "laptop": "dizüstü bilgisayar",
}


def _tr(label: str) -> str:
    return _LABEL_TR.get(label.lower(), label)


class VideoDetector:

    def __init__(self):
        self.model = YOLO(settings.yolo_model)
        self.confidence = settings.yolo_confidence
        self.frames_dir = Path(settings.frames_dir)
        self.frames_dir.mkdir(parents=True, exist_ok=True)
        self.event_logger = EventLogger()
        logger.info(f"YOLO modeli yüklendi: {settings.yolo_model}")

    # ── Bytes'tan analiz ────────────────────────────────────────────────────

    def analyze_frame_bytes(
        self,
        image_bytes: bytes,
        frame_id: str | None = None,
        timestamp: int | None = None,
        source_id: str = "camera",
    ) -> "pb2.AnalysisResult":
        frame_id = frame_id or str(uuid.uuid4())
        timestamp = timestamp or int(time.time() * 1000)

        nparr = np.frombuffer(image_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if frame is None:
            raise ValueError("Geçersiz görüntü verisi")
        return self._process(frame, frame_id, timestamp, source_id)

    # ── OpenCV frame'den analiz ─────────────────────────────────────────────

    def analyze_frame(
        self,
        frame: np.ndarray,
        frame_id: str | None = None,
        timestamp: int | None = None,
        source_id: str = "camera",
    ) -> "pb2.AnalysisResult":
        frame_id = frame_id or str(uuid.uuid4())
        timestamp = timestamp or int(time.time() * 1000)
        return self._process(frame, frame_id, timestamp, source_id)

    # ── İç işleme ───────────────────────────────────────────────────────────

    def _process(
        self,
        frame: np.ndarray,
        frame_id: str,
        timestamp: int,
        source_id: str,
    ) -> "pb2.AnalysisResult":
        results = self.model(frame, conf=self.confidence, verbose=False)

        detections: list[pb2.Detection] = []
        detected_objects: list[str] = []

        for r in results:
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                label = self.model.names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())

                color = dominant_color(frame, (x1, y1, x2, y2))
                label_tr = _tr(label)
                detected_objects.append(f"{color} {label_tr}" if color != "belirsiz" else label_tr)

                detections.append(
                    pb2.Detection(
                        label=label,
                        confidence=conf,
                        bbox=pb2.BBox(x1=x1, y1=y1, x2=x2, y2=y2),
                        color_hint=color,
                    )
                )

        # Kareyi annotate edip kaydet
        annotated = results[0].plot() if results else frame
        dt = datetime.fromtimestamp(timestamp / 1000)
        frame_filename = f"{dt.strftime('%Y%m%d_%H%M%S')}_{frame_id[:8]}.jpg"
        frame_path = str(self.frames_dir / frame_filename)
        cv2.imwrite(frame_path, annotated)

        # Olay metni üret
        event_description = ""
        if detected_objects:
            time_str = dt.strftime("%H:%M")
            objects_str = ", ".join(set(detected_objects))
            event_description = (
                f"{time_str} - {source_id} kamerasında tespit: {objects_str}"
            )
            self.event_logger.log(event_description, frame_path, timestamp)
            logger.info(event_description)

        return pb2.AnalysisResult(
            frame_id=frame_id,
            timestamp=timestamp,
            detections=detections,
            event_description=event_description,
            frame_saved=True,
            frame_path=frame_path,
        )
