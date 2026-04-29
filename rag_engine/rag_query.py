"""
RAG Sorgu Motoru

FAISS'ten ilgili olayları getirir, Claude API ile kullanıcı sorusunu yanıtlar.
Prompt caching ile tekrarlı sistem promtları cache'lenir.
"""
from typing import Any

import anthropic
from loguru import logger

from config import settings
from rag_engine.vector_store import VectorStore

_SYSTEM_PROMPT = """\
Sen bir akıllı güvenlik kamerası asistanısın.
Video kayıtlarından tespit edilen olaylar hakkında sorulan sorulara,
sana verilen olay kayıtlarını kullanarak Türkçe yanıt veriyorsun.

Yanıt verirken:
- Yalnızca sana verilen olay kayıtlarına dayan.
- Eğer sorguyla ilgili kayıt yoksa bunu açıkça belirt.
- Saat, nesne rengi ve tür gibi spesifik detayları öne çıkar.
- Kısa ve net ol.
"""

_CONTEXT_TEMPLATE = """\
Aşağıda kamera kayıtlarından alınan olay metinleri ve benzerlik skorları bulunmaktadır:

{events}

Kullanıcı sorusu: {query}
"""


class RAGQueryEngine:

    def __init__(self, vector_store: VectorStore | None = None):
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self._vector_store = vector_store or VectorStore()
        self._model = settings.llm_model
        logger.info(f"RAGQueryEngine hazır – model: {self._model}")

    # ── Ana sorgu ────────────────────────────────────────────────────────────

    def query(
        self,
        question: str,
        top_k: int | None = None,
        min_score: float | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        """
        Kullanıcı sorusunu RAG mimarisiyle yanıtlar.

        Returns:
            {
              "answer": str,
              "retrieved_events": list[dict],
              "usage": dict,
            }
        """
        # 1. İlgili olayları getir
        events = self._vector_store.search(question, top_k=top_k, min_score=min_score)

        if not events:
            return {
                "answer": (
                    "Kayıtlarda sorunuzla ilgili bir olay bulunamadı. "
                    "Sistem henüz herhangi bir olay kaydetmemiş olabilir."
                ),
                "retrieved_events": [],
                "usage": {},
            }

        # 2. Context oluştur
        events_text = "\n".join(
            f"[Skor: {e['score']:.2f}] {e['text']}" for e in events
        )
        user_content = _CONTEXT_TEMPLATE.format(events=events_text, query=question)

        # 3. Claude API çağrısı — prompt caching aktif
        if stream:
            answer, usage = self._stream_query(user_content)
        else:
            answer, usage = self._sync_query(user_content)

        return {
            "answer": answer,
            "retrieved_events": events,
            "usage": usage,
        }

    # ── Senkron sorgu ────────────────────────────────────────────────────────

    def _sync_query(self, user_content: str) -> tuple[str, dict]:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    # Sistem promptu sabit olduğu için cache'lenir
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        )
        answer = next(
            (b.text for b in response.content if b.type == "text"), ""
        )
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                response.usage, "cache_read_input_tokens", 0
            ),
            "cache_creation_input_tokens": getattr(
                response.usage, "cache_creation_input_tokens", 0
            ),
        }
        logger.debug(f"LLM kullanımı: {usage}")
        return answer, usage

    # ── Akış sorgusu ─────────────────────────────────────────────────────────

    def _stream_query(self, user_content: str) -> tuple[str, dict]:
        with self._client.messages.stream(
            model=self._model,
            max_tokens=1024,
            system=[
                {
                    "type": "text",
                    "text": _SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=[{"role": "user", "content": user_content}],
        ) as stream:
            answer = ""
            for text in stream.text_stream:
                answer += text
                print(text, end="", flush=True)
            print()
            final = stream.get_final_message()

        usage = {
            "input_tokens": final.usage.input_tokens,
            "output_tokens": final.usage.output_tokens,
            "cache_read_input_tokens": getattr(
                final.usage, "cache_read_input_tokens", 0
            ),
            "cache_creation_input_tokens": getattr(
                final.usage, "cache_creation_input_tokens", 0
            ),
        }
        return answer, usage

    # ── Toplu indeksleme ─────────────────────────────────────────────────────

    def index_events_from_logger(self, event_logger) -> int:
        """EventLogger'dan tüm olayları okuyup VectorStore'a ekler."""
        events = event_logger.load_all()
        if not events:
            return 0
        texts = [e["description"] for e in events]
        metas = [
            {
                "timestamp": e["timestamp"],
                "datetime": e["datetime"],
                "frame_path": e.get("frame_path", ""),
            }
            for e in events
        ]
        self._vector_store.add_events_batch(texts, metas)
        logger.info(f"{len(events)} olay VectorStore'a eklendi")
        return len(events)
