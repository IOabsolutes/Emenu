from __future__ import annotations

from typing import List
from pydantic import BaseModel
from pathlib import Path

from src.domain.ports.ocr_service import OCRService
from src.domain.ports.llm_classifier import LLMClassifier


class AnalyzeResult(BaseModel):
    filename: str
    doc_type: str
    processing_seconds: float
    number_and_date_lines: List[str]
    counterparties_lines: List[str]
    requisites_lines: List[str]


class AnalyzeDocumentUseCase:
    def __init__(self, ocr_service: OCRService, llm: LLMClassifier) -> None:
        self._ocr = ocr_service
        self._llm = llm

    def execute(self, pdf_path: Path) -> AnalyzeResult:
        easy_texts, tess_texts = self._ocr.extract_full_document_texts(pdf_path)
        easy_first, tess_first = easy_texts[0], tess_texts[0]

        doc_type = self._llm.classify_document(easy_first, tess_first)
        number_date = self._llm.extract_number_date(doc_type, easy_first, tess_first)
        parties = self._llm.extract_counterparties(doc_type, easy_first, tess_first)
        requisites = self._llm.extract_requisites(
            parties, "\n".join(easy_texts), "\n".join(tess_texts)
        )

        return AnalyzeResult(
            filename=pdf_path.name,
            doc_type=doc_type,
            processing_seconds=0.0,
            number_and_date_lines=[ln for ln in number_date.splitlines() if ln.strip()],
            counterparties_lines=[ln for ln in parties.splitlines() if ln.strip()],
            requisites_lines=[ln for ln in requisites.splitlines() if ln.strip()],
        )
