"""Strict government warning check."""
import re
from rapidfuzz import fuzz

HEADER = "GOVERNMENT WARNING:"
BODY = ("(1) According to the Surgeon General, women should not drink alcoholic "
        "beverages during pregnancy because of the risk of birth defects. (2) "
        "Consumption of alcoholic beverages impairs your ability to drive a car or "
        "operate machinery, and may cause health problems.")


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def check_warning(ocr_text: str) -> tuple[str, str]:
    """Return (status, message). Status: Match / Needs Review / Mismatch."""
    flat = re.sub(r"\s+", " ", ocr_text)
    if HEADER not in flat:
        if re.search(r"government\s+warning", flat, re.I):
            return "Mismatch", "'GOVERNMENT WARNING:' must be all capitals with a colon."
        return "Mismatch", "Government warning not found on the label."
    # Compare the text after the header against the required wording
    tail = flat.split(HEADER, 1)[1]
    score = fuzz.partial_ratio(_norm(BODY), _norm(tail[: len(BODY) + 40]))
    if score >= 98:
        return "Match", "Warning text matches. Check by eye that the header is bold."
    if score >= 90:
        return "Needs Review", f"Warning is close ({score:.0f}%). Possible OCR error or wording change."
    return "Mismatch", f"Warning wording differs from the required text ({score:.0f}% similar)."
