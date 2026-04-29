"""
Tespit olaylarını hem log dosyasına hem JSON satır dosyasına yazar.
Bu olaylar daha sonra FAISS'e indexlenir.
"""
import json
from datetime import datetime
from pathlib import Path

from loguru import logger

from config import settings


class EventLogger:

    def __init__(self):
        self.events_dir = Path(settings.events_dir)
        self.events_dir.mkdir(parents=True, exist_ok=True)
        today = datetime.now().strftime("%Y%m%d")
        self.events_file = self.events_dir / f"events_{today}.jsonl"

    def log(self, description: str, frame_path: str, timestamp: int) -> None:
        entry = {
            "timestamp": timestamp,
            "datetime": datetime.fromtimestamp(timestamp / 1000).isoformat(),
            "description": description,
            "frame_path": frame_path,
        }
        with open(self.events_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def load_today(self) -> list[dict]:
        if not self.events_file.exists():
            return []
        events = []
        with open(self.events_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def load_all(self) -> list[dict]:
        events = []
        for path in sorted(self.events_dir.glob("events_*.jsonl")):
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        events.append(json.loads(line))
        return events
