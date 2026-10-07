"""Pull numeric fields out of OCR text and normalize them for comparison."""
import re

ML_PER = {"ml": 1.0, "l": 1000.0, "cl": 10.0, "fl oz": 29.5735, "oz": 29.5735}


def parse_abv(text: str) -> float | None:
    """'45% Alc./Vol. (90 Proof)' -> 45.0. Falls back to proof / 2."""
    m = re.search(r"(\d{1,2}(?:\.\d+)?)\s*%", text)
    if m:
        return float(m.group(1))
    m = re.search(r"(\d{2,3}(?:\.\d+)?)\s*proof", text, re.I)
    return float(m.group(1)) / 2 if m else None


def parse_volume_ml(text: str) -> float | None:
    """'750 mL' / '0.75 L' / '25.4 fl. oz.' -> millilitres."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*(ml|cl|l|fl\.?\s*oz|oz)\b", text, re.I)
    if not m:
        return None
    unit = re.sub(r"[.\s]+", " ", m.group(2).lower()).strip()
    unit = "fl oz" if unit.startswith("fl") else unit
    return float(m.group(1).replace(",", ".")) * ML_PER[unit]
