from __future__ import annotations

import re
from datetime import datetime
from typing import List


def normalize_dates(lines: List[str]) -> List[str]:
    MONTHS_MAP = {
        "янв": "01",
        "фев": "02",
        "мар": "03",
        "апр": "04",
        "мая": "05",
        "май": "05",
        "июн": "06",
        "июл": "07",
        "авг": "08",
        "сен": "09",
        "сент": "09",
        "окт": "10",
        "ноя": "11",
        "дек": "12",
    }

    def fix_month_text(text: str) -> str | None:
        text = text.lower()
        for key, val in MONTHS_MAP.items():
            if key in text:
                return val
        return None

    def try_parse_date(s: str) -> str | None:
        s = s.strip()
        month_match = re.search(r"\d{1,2}\s+([а-яА-ЯёЁ]{3,})\s+\d{2,4}", s)
        if month_match:
            parts = s.split()
            if len(parts) >= 3:
                day = re.sub(r"\D", "", parts[0])
                month_txt = parts[1]
                year = re.sub(r"\D", "", parts[2])
                if not (day and year):
                    return None
                month_num = fix_month_text(month_txt)
                if month_num:
                    try:
                        return f"{int(year):04d}-{month_num}-{int(day):02d}"
                    except Exception:
                        return None

        s = re.sub(r"\s*([./\-])\s*", r"\1", s)
        formats = [
            "%d.%m.%Y",
            "%d.%m.%y",
            "%d-%m-%Y",
            "%d-%m-%y",
            "%d/%m/%Y",
            "%d/%m/%y",
            "%Y-%m-%d",
            "%Y/%m/%d",
            "%d %m %Y",
            "%d %m %y",
        ]
        for fmt in formats:
            try:
                d = datetime.strptime(s, fmt)
                return d.strftime("%Y-%m-%d")
            except Exception:
                continue
        return None

    iso_lines: List[str] = []
    for line in lines:
        if line.lower().startswith("дата:"):
            original = line
            date_part = line.split(":", 1)[1].strip()
            iso_date = try_parse_date(date_part)
            if iso_date:
                iso_lines.append(f"дата: {iso_date}")
            else:
                iso_lines.append(original)
        else:
            iso_lines.append(line)
    return iso_lines


def unique_lines(lines: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []
    for line in lines:
        if line not in seen:
            result.append(line)
            seen.add(line)
    return result


def clean_doc_number(raw_number_line: str) -> str:
    if not raw_number_line.lower().startswith("номер:"):
        return raw_number_line.strip()

    content = raw_number_line.split(":", 1)[1].strip()
    content = re.sub(r"\bN[оo0g°:]{1}\s*", "№ ", content, flags=re.IGNORECASE)
    content = re.sub(
        r"^(акт|договор|счет-фактура|счет|упд|акт выполненных работ)\b",
        "",
        content,
        flags=re.IGNORECASE,
    ).strip()
    if "№" in content:
        content = content.split("№", 1)[-1].strip()
    content = re.sub(
        r"^(номер|дата)\s*[:\-]?", "", content, flags=re.IGNORECASE
    ).strip()
    if re.fullmatch(r"\d{1,2}[\s./-]\d{1,2}[\s./-]\d{2,4}", content):
        return "<не найдено>"
    if not re.search(r"\d", content):
        return "<не найдено>"
    return content if content else "<не найдено>"
