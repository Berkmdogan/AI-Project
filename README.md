# Akıllı Video Analiz & RAG Asistanı

OpenCV + YOLOv8 tabanlı video analizi ve FAISS + Claude RAG motoru ile güvenlik kamerası görüntülerini sorgulayabileceğiniz bir sistem.

## Mimari

```
┌─────────────────────────────────────────────────────┐
│  Video Kaynağı (OpenCV / gRPC stream)               │
│           ↓                                          │
│  YOLOv8 Nesne Tespiti + Renk Algılama               │
│           ↓                                          │
│  Olay Metni: "09:15 - Kırmızı araç tespit edildi"   │
│           ↓                                          │
│  Sentence-Transformers Embedding → FAISS Index      │
│           ↓                                          │
│  RAG Sorgu: "Kırmızı araç geldi mi?" → Claude API   │
│           ↓                                          │
│  FastAPI REST + gRPC Servisleri                     │
└─────────────────────────────────────────────────────┘
```

## Dizin Yapısı

```
AI-Project/
├── video_analyzer/      # OpenCV + YOLO pipeline
│   ├── detector.py      # Frame analizi
│   ├── color_detector.py# Renk tespiti
│   └── event_logger.py  # JSONL olay kaydı
├── grpc_service/        # gRPC video stream servisi
│   ├── proto/           # .proto tanımları
│   ├── server.py        # gRPC sunucusu
│   └── client.py        # gRPC istemcisi
├── rag_engine/          # RAG motoru
│   ├── embedder.py      # Sentence-Transformers
│   ├── vector_store.py  # FAISS vektör deposu
│   └── rag_query.py     # Claude API entegrasyonu
├── api/                 # FastAPI REST arayüzü
│   ├── main.py          # Uygulama giriş noktası
│   ├── routes.py        # Endpoint tanımları
│   └── models.py        # Pydantic modelleri
├── tests/               # Unit testler
├── scripts/             # Demo ve yardımcı scriptler
└── docker/              # Dockerfile'lar
```

## Kurulum

### 1. Ortam değişkenlerini ayarlayın

```bash
cp .env.example .env
# .env dosyasını düzenleyip ANTHROPIC_API_KEY'i ekleyin
```

### 2. Bağımlılıkları yükleyin

```bash
pip install -r requirements.txt
```

### 3. Proto stub'larını oluşturun

```bash
bash grpc_service/generate_proto.sh
```

### 4. Demo çalıştırın

```bash
python scripts/demo.py
```

## Docker ile Çalıştırma

```bash
docker-compose up --build
```

Servisler:
- **API**: http://localhost:8000 (Swagger UI: http://localhost:8000/docs)
- **gRPC**: localhost:50051

## API Kullanımı

### Görüntü analizi

```bash
curl -X POST http://localhost:8000/api/v1/analyze/frame \
  -F "file=@kamera_karesi.jpg" \
  -F "source_id=giris_kamerasi"
```

### RAG sorgusu

```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"question": "Bugün kırmızı araçlı biri geldi mi?"}'
```

### Yanıt örneği

```json
{
  "answer": "Evet, bugün iki farklı saatte kırmızı araç tespit edildi: 08:15'te giriş kamerasında ve 11:20'de otopark kamerasında.",
  "retrieved_events": [
    {"text": "08:15 - giris_kamerasi: kırmızı araç, kişi", "score": 0.92, "frame_path": "..."},
    {"text": "11:20 - otopark_kamerasi: kırmızı araç", "score": 0.88, "frame_path": "..."}
  ],
  "usage": {"input_tokens": 412, "output_tokens": 67, "cache_read_input_tokens": 380}
}
```

## Testler

```bash
pytest tests/ -v
```

## Teknoloji Yığını

| Katman | Teknoloji |
|--------|-----------|
| Nesne Tespiti | YOLOv8 (Ultralytics) |
| Video İşleme | OpenCV |
| Vektör DB | FAISS (IndexFlatIP) |
| Embedding | sentence-transformers / all-MiniLM-L6-v2 |
| LLM | Claude (Anthropic API) + Prompt Caching |
| Transport | gRPC (proto3) |
| REST API | FastAPI + Uvicorn |
| Container | Docker Compose |
