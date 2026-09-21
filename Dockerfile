# API do avaliador Calligraphos (CPU). Build: docker build -t calligraphos-api .
# Rodar: docker run -p 8000:8000 -v ./google_credentials.json:/app/google_credentials.json:ro calligraphos-api
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends fontconfig fonts-dejavu-core fonts-liberation fonts-noto-core libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements.txt
COPY calligraphos ./calligraphos
COPY config.json modelo_caligrafia.pth ./
ENV PORTA=8000
EXPOSE 8000
CMD ["python", "-m", "calligraphos.api"]
