"""
Demo scripti: RAG pipeline'ını simüle edilmiş verilerle çalıştırır.

Gerçek kamera olmadan sistemi test etmek için sentetik olaylar üretir,
VectorStore'a ekler, ardından örnek sorgular yapar.
"""
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# Proje kökünü path'e ekle
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from rag_engine.vector_store import VectorStore
from rag_engine.rag_query import RAGQueryEngine

console = Console()


# ── Sentetik olay verisi ─────────────────────────────────────────────────────

SYNTHETIC_EVENTS = [
    {
        "text": "08:15 - giris_kamerasi kamerasında tespit: kırmızı araç, kişi",
        "timestamp": int((datetime.now().replace(hour=8, minute=15)).timestamp() * 1000),
        "frame_path": "data/frames/demo_001.jpg",
        "source_id": "giris_kamerasi",
    },
    {
        "text": "09:32 - otopark_kamerasi kamerasında tespit: mavi araç",
        "timestamp": int((datetime.now().replace(hour=9, minute=32)).timestamp() * 1000),
        "frame_path": "data/frames/demo_002.jpg",
        "source_id": "otopark_kamerasi",
    },
    {
        "text": "10:45 - giris_kamerasi kamerasında tespit: kişi, sırt çantası",
        "timestamp": int((datetime.now().replace(hour=10, minute=45)).timestamp() * 1000),
        "frame_path": "data/frames/demo_003.jpg",
        "source_id": "giris_kamerasi",
    },
    {
        "text": "11:20 - otopark_kamerasi kamerasında tespit: kırmızı araç, kırmızı araç",
        "timestamp": int((datetime.now().replace(hour=11, minute=20)).timestamp() * 1000),
        "frame_path": "data/frames/demo_004.jpg",
        "source_id": "otopark_kamerasi",
    },
    {
        "text": "13:05 - arka_kapi_kamerasi kamerasında tespit: kişi, el çantası",
        "timestamp": int((datetime.now().replace(hour=13, minute=5)).timestamp() * 1000),
        "frame_path": "data/frames/demo_005.jpg",
        "source_id": "arka_kapi_kamerasi",
    },
    {
        "text": "14:30 - giris_kamerasi kamerasında tespit: beyaz araç, kişi",
        "timestamp": int((datetime.now().replace(hour=14, minute=30)).timestamp() * 1000),
        "frame_path": "data/frames/demo_006.jpg",
        "source_id": "giris_kamerasi",
    },
    {
        "text": "15:55 - otopark_kamerasi kamerasında tespit: siyah araç",
        "timestamp": int((datetime.now().replace(hour=15, minute=55)).timestamp() * 1000),
        "frame_path": "data/frames/demo_007.jpg",
        "source_id": "otopark_kamerasi",
    },
    {
        "text": "16:10 - arka_kapi_kamerasi kamerasında tespit: köpek, kişi",
        "timestamp": int((datetime.now().replace(hour=16, minute=10)).timestamp() * 1000),
        "frame_path": "data/frames/demo_008.jpg",
        "source_id": "arka_kapi_kamerasi",
    },
]

DEMO_QUERIES = [
    "Bugün kırmızı araçlı biri geldi mi?",
    "Kaç farklı araç rengi tespit edildi?",
    "Giriş kamerasında neler görüldü?",
    "Köpek görüldü mü?",
    "Saat 10:00 ile 15:00 arasında neler oldu?",
]


def run_demo():
    console.print(Panel.fit(
        "[bold cyan]Akıllı Video Analiz & RAG Asistanı - Demo[/bold cyan]\n"
        "Simüle edilmiş güvenlik kamerası verileriyle RAG pipeline'ı test ediliyor.",
        border_style="cyan",
    ))

    # ── 1. VectorStore'u başlat ve olayları ekle ─────────────────────────────
    console.print("\n[bold]1. Sentetik olaylar VectorStore'a ekleniyor...[/bold]")

    vs = VectorStore()
    vs.reset()  # temiz başlangıç

    texts = [e["text"] for e in SYNTHETIC_EVENTS]
    metas = [
        {
            "timestamp": e["timestamp"],
            "datetime": datetime.fromtimestamp(e["timestamp"] / 1000).isoformat(),
            "frame_path": e["frame_path"],
            "source_id": e["source_id"],
        }
        for e in SYNTHETIC_EVENTS
    ]
    vs.add_events_batch(texts, metas)
    console.print(f"  [green]✓[/green] {vs.total_events} olay eklendi")

    # ── 2. Olayları göster ───────────────────────────────────────────────────
    table = Table(title="İndekslenen Olaylar", show_header=True)
    table.add_column("Zaman", style="cyan")
    table.add_column("Olay", style="white")
    table.add_column("Kaynak", style="yellow")
    for e in SYNTHETIC_EVENTS:
        dt = datetime.fromtimestamp(e["timestamp"] / 1000).strftime("%H:%M")
        table.add_row(dt, e["text"].split(" - ", 1)[-1], e["source_id"])
    console.print(table)

    # ── 3. RAG sorguları yap ─────────────────────────────────────────────────
    console.print("\n[bold]2. RAG sorguları çalıştırılıyor...[/bold]\n")

    engine = RAGQueryEngine(vector_store=vs)

    for i, question in enumerate(DEMO_QUERIES, 1):
        console.print(f"[bold yellow]Soru {i}:[/bold yellow] {question}")
        try:
            result = engine.query(question, top_k=3)
            console.print(Panel(
                result["answer"],
                title="[green]Yanıt[/green]",
                border_style="green",
            ))
            if result["retrieved_events"]:
                console.print("  İlgili olaylar:")
                for ev in result["retrieved_events"]:
                    score = ev.get("score", 0)
                    console.print(f"    [dim]• [{score:.2f}] {ev['text']}[/dim]")
            usage = result.get("usage", {})
            if usage:
                console.print(
                    f"  [dim]Token kullanımı: giriş={usage.get('input_tokens', 0)}, "
                    f"çıkış={usage.get('output_tokens', 0)}, "
                    f"cache={usage.get('cache_read_input_tokens', 0)} okundu[/dim]"
                )
        except Exception as exc:
            console.print(f"  [red]Hata: {exc}[/red]")
        console.print()

    console.print(Panel.fit(
        "[bold green]Demo tamamlandı![/bold green]\n"
        "Gerçek kullanım için:\n"
        "  1. .env dosyasına ANTHROPIC_API_KEY ekleyin\n"
        "  2. docker-compose up ile servisleri başlatın\n"
        "  3. http://localhost:8000/docs adresinden API'yi deneyin",
        border_style="green",
    ))


if __name__ == "__main__":
    run_demo()
