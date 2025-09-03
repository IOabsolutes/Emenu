from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image
import cv2
from pdf2image import convert_from_path
import easyocr
import pytesseract

from src.domain.ports.ocr_service import OCRService
from src.logger_config import get_logger


logger = get_logger(__name__)


def _estimate_skew_angle(pil_img: Image.Image) -> float:
    img = np.array(pil_img.convert("L"))
    blur = cv2.GaussianBlur(img, (9, 9), 0)
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    coords = np.column_stack(np.where(binary > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    elif angle > 45:
        angle = angle - 90
    return -angle


def _deskew_image(pil_img: Image.Image, angle: float) -> Image.Image:
    img = np.array(pil_img)
    (h, w) = img.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(
        img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
    )
    return Image.fromarray(rotated)


class EasyTesseractOCRService(OCRService):
    def __init__(self, use_gpu: bool = True) -> None:
        self._reader = easyocr.Reader(["ru", "en"], gpu=use_gpu)

    def extract_full_document_texts(
        self, pdf_path: Path, dpi: int = 300, thread_count: int = 4
    ) -> Tuple[List[str], List[str]]:
        pages = convert_from_path(
            str(pdf_path), dpi=dpi, fmt="png", thread_count=thread_count
        )
        easy_texts: List[str] = []
        tess_texts: List[str] = []
        for idx, page in enumerate(pages):
            if idx == 0:
                angle = _estimate_skew_angle(page)
                logger.info(f"First page skew angle: {angle:.2f}°")
                if abs(angle) > 1.5:
                    page = _deskew_image(page, angle)

            img = np.array(page)
            easy_lines = self._reader.readtext(
                img, detail=0, paragraph=True, y_ths=-0.1, x_ths=1.0
            )
            easy_texts.append("\n".join(easy_lines))

            gray = page.convert("L")
            tess_txt = pytesseract.image_to_string(gray, lang="rus+eng")
            tess_texts.append(tess_txt.strip())
        return easy_texts, tess_texts

    def extract_first_page_texts(
        self, pdf_path: Path, dpi: int = 300
    ) -> Tuple[str, str]:
        pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=1, last_page=1)
        if not pages:
            return "", ""
        page = pages[0]
        angle = _estimate_skew_angle(page)
        logger.info(f"First page skew angle: {angle:.2f}°")
        if abs(angle) > 1.5:
            page = _deskew_image(page, angle)
        img = np.array(page)
        easy_lines = self._reader.readtext(
            img, detail=0, paragraph=True, y_ths=-0.1, x_ths=1.0
        )
        easy_text = "\n".join(easy_lines)
        gray = page.convert("L")
        tess_text = pytesseract.image_to_string(gray, lang="rus+eng").strip()
        return easy_text, tess_text
