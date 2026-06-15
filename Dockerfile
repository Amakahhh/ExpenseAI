FROM python:3.11-slim

# Install Tesseract OCR with root permissions (Docker build context has root)
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        libglib2.0-0 \
        libsm6 \
        libxext6 \
        libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY smart-expense-system/backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY smart-expense-system/backend/ .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
