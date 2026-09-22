# API do avaliador Calligraphos (CPU). Build: docker build -t calligraphos-api .
# Rodar: docker run -p 8000:8000 -v ./google_credentials.json:/app/google_credentials.json:ro calligraphos-api
FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends fontconfig fonts-dejavu-core fonts-liberation fonts-noto-core libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-api.txt .
RUN pip install --no-cache-dir torch==2.11.0 torchvision==0.26.0 --index-url https://download.pytorch.org/whl/cpu \
 && pip install --no-cache-dir -r requirements-api.txt
COPY calligraphos ./calligraphos
COPY config.json modelo_caligrafia.pth ./
ENV PORTA=8000
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/saude').status==200 else 1)"
CMD ["python", "-m", "calligraphos.api"]
