from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Tuple


class OCRService(ABC):
    """Port interface for OCR operations over PDF documents.

    Implementations provide text extracted by different engines (e.g., EasyOCR and Tesseract).
    """

    @abstractmethod
    def extract_full_document_texts(self, pdf_path: Path, dpi: int = 300, thread_count: int = 4) -> Tuple[List[str], List[str]]:
        """Return per-page texts for the whole document.

        Returns a tuple (easy_texts, tess_texts) where each is a list of page strings.
        """

    @abstractmethod
    def extract_first_page_texts(self, pdf_path: Path, dpi: int = 300) -> Tuple[str, str]:
        """Return texts for the first page only as a tuple (easy_text, tess_text)."""


