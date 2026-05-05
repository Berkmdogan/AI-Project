FROM python:3.11-slim

WORKDIR /app

COPY trading_ai/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "trading_ai.ui_layer.api:app", "--host", "0.0.0.0", "--port", "8000"]
