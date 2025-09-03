from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import re
import uuid
import json

from src.domain.ports.ocr_service import OCRService


PriceMatch = Tuple[str, Optional[float]]


def _is_section_heading(line: str) -> bool:
    text = line.strip()
    if len(text) < 3:
        return False
    # Accept ALL CAPS and Title Case words (e.g., "Leading Off") of 2+ tokens
    if any(ch.islower() for ch in text):
        # Allow simple Title Case with 2+ words
        words = text.split()
        if len(words) >= 2 and all(w[:1].isupper() and w[1:].islower() for w in words if w):
            pass
        else:
            return False
    if re.search(r"[\$€£]\s*\d", text):
        return False
    if re.search(r"\d+\s*[.,]?\d{0,2}$", text):
        return False
    return True


def _extract_price(token_line: str) -> PriceMatch:
    # Try to find a price token in the line
    # Examples: $12, 12, 12.50, 12,50, USD 12, $12.00
    m = re.search(r"(\$\s*\d+[\.,]?\d{0,2}|\b\d+[\.,]?\d{0,2}\b)", token_line)
    if not m:
        return ("", None)
    raw = m.group(1).replace(" ", "")
    # If it contains currency sign, keep as-is per requirement
    if "$" in raw or "€" in raw or "£" in raw:
        return (raw, None)
    # Try parse numeric
    try:
        numeric = float(raw.replace(",", "."))
        return (raw, numeric)
    except ValueError:
        return (raw, None)


class ParseMenuUseCase:
    def __init__(self, ocr_service: OCRService, llm_service: Optional[Any] = None) -> None:
        self._ocr = ocr_service
        self._llm = llm_service

    def execute(self, pdf_path: Path) -> List[Dict]:
        easy_text, tess_text = self._ocr.extract_first_page_texts(pdf_path)
        # Prefer EasyOCR for layout grouping; fallback to tess
        text = easy_text.strip() if easy_text.strip() else tess_text.strip()
        lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]

        items: List[Dict] = []
        current_category: Optional[str] = None
        current_dish: Optional[Dict] = None

        def flush_current() -> None:
            nonlocal current_dish
            if current_dish:
                # Normalize description
                desc = " ".join(
                    [seg.strip() for seg in current_dish.get("description_parts", [])]
                ).strip()
                if desc:
                    current_dish["description"] = desc
                current_dish.pop("description_parts", None)
                items.append(current_dish)
                current_dish = None

        for line in lines:
            if _is_section_heading(line):
                # Starting a new section/category
                flush_current()
                current_category = line.strip()
                continue

            # If we have an ongoing dish and this looks like a continuation/description line
            if current_dish is not None:
                if not _is_section_heading(line):
                    # Heuristic: continuation if line starts lowercase or is indented or has no price-like token
                    _, maybe_num = _extract_price(line)
                    if (line[:1].islower() or line[:1].isspace() or maybe_num is None) and not re.match(
                        r"^[A-Z\s\-\'\&]+$", line.strip()
                    ):
                        current_dish.setdefault("description_parts", []).append(line)
                        continue
                # Otherwise flush and treat as new dish line
                flush_current()

            # Try to parse a dish line: name possibly followed by price
            price_raw, price_num = _extract_price(line)
            if price_raw:
                # Split name and price region
                name_part = line[: line.find(price_raw)].strip(" -:·.") or line.strip()
            else:
                name_part = line.strip()

            # Basic guard: name shouldn’t be a section heading
            if _is_section_heading(name_part):
                current_category = name_part
                continue

            dish: Dict = {
                "dish_id": uuid.uuid4().hex,
                "dish_name": name_part,
                "category": (current_category or "UNCATEGORIZED"),
            }
            if price_raw:
                if price_num is not None:
                    dish["price"] = price_num
                else:
                    dish["price"] = price_raw

            # Normalize category to uppercase for consistent output
            dish["category"] = str(dish["category"]).upper()
            current_dish = dish

        # Final flush
        flush_current()

        # Filter out junk: require dish_name present
        heuristic_items: List[Dict] = []
        for it in items:
            name = (it.get("dish_name") or "").strip()
            if not name:
                continue
            heuristic_items.append(it)

        # If LLM is available, try to refine/replace with model output first
        if self._llm and (text.strip()):
            try:
                prompt = (
                    "You are a structured data extractor.\n"
                    "Given the first page of a restaurant menu text, extract menu items as a JSON array.\n"
                    "For each item, include: dish_name (string, required), price (float if clearly numeric; if the text shows a token like '$14', keep that exact string), description (string, optional), category (string, section heading in ALL CAPS).\n"
                    "Do not include any additional commentary. Output ONLY valid JSON.\n\n"
                    "Menu text follows:\n" + text
                )
                raw = self._llm._post_prompt(prompt)  # type: ignore[attr-defined]
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    model_items: List[Dict] = []
                    for obj in parsed:
                        if not isinstance(obj, dict):
                            continue
                        dish_name = str(obj.get("dish_name", "")).strip()
                        if not dish_name:
                            continue
                        out: Dict = {
                            "dish_id": uuid.uuid4().hex,
                            "dish_name": dish_name,
                            "category": str(obj.get("category", "UNCATEGORIZED")).strip() or "UNCATEGORIZED",
                        }
                        # price normalization: keep token if includes currency sign, else numeric if float
                        price_val = obj.get("price")
                        if isinstance(price_val, (int, float)):
                            out["price"] = float(price_val)
                        elif isinstance(price_val, str):
                            if any(sym in price_val for sym in ["$", "€", "£"]):
                                out["price"] = price_val.strip()
                            else:
                                try:
                                    out["price"] = float(price_val.replace(",", "."))
                                except Exception:
                                    out["price"] = price_val.strip()
                        desc = str(obj.get("description", "")).strip()
                        if desc:
                            out["description"] = desc
                        model_items.append(out)
                    if model_items:
                        return model_items
            except Exception:
                # Fallback to heuristic if LLM fails
                pass

        return heuristic_items


