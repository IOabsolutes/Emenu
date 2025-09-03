from __future__ import annotations

from src.config import settings
from src.infrastructure.ocr.easy_tesseract_ocr import EasyTesseractOCRService
from src.application.use_cases.parse_menu import ParseMenuUseCase
from src.infrastructure.llm.ollama_llm import OllamaLLM


# Adapters
ocr_service = EasyTesseractOCRService(use_gpu=settings.use_gpu)
llm_service = OllamaLLM(api_url=settings.ollama_api_url, model=settings.ollama_model)

# Use cases
parse_menu_use_case = ParseMenuUseCase(ocr_service, llm_service)
