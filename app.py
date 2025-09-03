from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
import shutil
import uuid
import json
import time
from typing import Any

from src.config import settings
from src.presentation.container import (
    parse_menu_use_case,
)

from src.logger_config import get_logger

# No text utils needed for minimal scope


logger = get_logger(__name__)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@app.post("/menu/parse")
async def parse_menu(file: UploadFile = File(...), format: str = "object"):
    start_time = time.perf_counter()
    logger.info(f"[Menu] Received file: {file.filename}")

    pdf_id = uuid.uuid4().hex
    pdf_path = UPLOAD_DIR / f"{pdf_id}.pdf"

    try:
        with pdf_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"[Menu] File saved: {pdf_path}")

        items = parse_menu_use_case.execute(pdf_path)
        elapsed = round(time.perf_counter() - start_time, 2)

        result = {
            "filename": file.filename,
            "processing_seconds": elapsed,
            "items": items,
        }

        json_path = UPLOAD_DIR / f"{pdf_id}_menu.json"
        with json_path.open("w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        logger.info(f"[Menu] Result saved: {json_path}")

        return JSONResponse(
            {
                "status": "ok",
                "pdf_id": pdf_id,
                "download": f"/download/{pdf_id}_menu.json",
                "result": result,
            }
        )
    except Exception as e:
        logger.error(f"[Menu] Error parsing menu {file.filename}: {e}")
        return JSONResponse(
            {"status": "error", "message": "File processing error."}, status_code=500
        )


@app.get("/download/{filename}")
async def download_result(filename: str):
    file_path = UPLOAD_DIR / filename
    if not file_path.exists():
        logger.error(f"File not found for download: {filename}")
        return JSONResponse(
            {"status": "error", "message": "File not found."}, status_code=404
        )
    logger.info(f"Serving file: {filename}")
    return FileResponse(file_path, media_type="application/json", filename=filename)
