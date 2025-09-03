# DataMind – Deployment Guide (Menu Parser)

## Requirements

- Ubuntu Server 22.04
- NVIDIA GPU with drivers and CUDA (optional but recommended)
- Docker + Docker Compose
- Installed locally or in container:
  - Tesseract OCR (rus+eng)
  - Ollama with model qwen:4b (or qwen3:4b)

---

## Install dependencies on server

```bash
# OCR
sudo apt update
sudo apt install -y tesseract-ocr tesseract-ocr-rus

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen:4b
ollama serve &
```

---

## 📦 Deploy project

```bash
# Clone
git clone <your-repo>
cd <your-repo>

# Docker
sudo apt install -y docker.io docker-compose
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
newgrp docker

# Run
docker compose build
docker compose up -d
```

---

## Verify

Service exposes two endpoints aligned with the Memory Bank minimal scope:

- POST `/menu/parse` – upload a PDF, parse page 1 food sections into JSON
- GET `/download/{filename}` – download previously saved JSON

Example (parse and get object response):

```bash
curl -X POST "http://<HOST>/menu/parse" \
     -H "Content-Type: multipart/form-data" \
     -F "file=@/path/to/menu.pdf"
```

Response (example):

```json
{
  "status": "ok",
  "pdf_id": "<uuid>",
  "download": "/download/<uuid>_menu.json",
  "result": {
    "filename": "menu.pdf",
    "processing_seconds": 1.23,
    "items": [
      {
        "dish_id": "...",
        "dish_name": "Classic Burger",
        "price": 14.0,
        "description": "Beef patty, cheddar, pickles",
        "category": "BURGERS"
      }
    ]
  }
}
```

---

## Where results are stored

- PDF and JSON are saved in the container:
  `/app/uploads/{uuid}.pdf` and `/app/uploads/{uuid}_menu.json`

- Download JSON:
  `http://<HOST>/download/{uuid}_menu.json`

---

## Common issues

| Issue                | Fix                                                 |
| -------------------- | --------------------------------------------------- |
| LLM not responding   | Ensure `ollama serve` is running                    |
| LLM connection error | Check IP `172.17.0.1`, port `11434`                 |
| GPU not used         | Verify `nvidia-smi` and drivers installed           |
| OCR not working      | Check `tesseract --version` and `tesseract-ocr-rus` |

---

## Notes

- Page 1 parsing only. Sections like "Leading Off", "Slider Towers", "Burgers", "Main Event" are detected (ALL CAPS and Title Case).
- Output fields per item: `dish_id` (auto), `dish_name` (required), `price` (float if numeric; if token includes currency like "$14" it is kept as-is), `description` (merged continuation lines), `category` (UPPERCASE).
- The parser uses OCR (EasyOCR + Tesseract) and optionally refines via Ollama (qwen:4b) to produce structured JSON. If the model fails to return valid JSON, heuristics are used.

---
