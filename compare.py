"""Compare application values with what the label says."""
import re
from dataclasses import dataclass
from rapidfuzz import fuzz
from extract import parse_abv, parse_volume_ml

MATCH, REVIEW, MISMATCH = "Match", "Needs Review", "Mismatch"


@dataclass
class Result:
    field: str
    status: str
    expected: str
    found: str
    note: str = ""


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", s.lower().replace("'", "")).strip()


def _text_field(name: str, expected: str, ocr_text: str) -> Result:
    """Brand / class: look for the expected text inside the OCR text."""
    flat = re.sub(r"\s+", " ", ocr_text)
    if expected in flat:
        return Result(name, MATCH, expected, expected)
    n_exp, n_txt = _norm(expected), _norm(flat)
    if n_exp and n_exp in n_txt:
        return Result(name, MATCH, expected, expected,
                      "Differs only in capitalization or punctuation.")
    score = fuzz.partial_ratio(n_exp, n_txt)
    if score >= 85:
        return Result(name, REVIEW, expected, "(close match)", f"{score:.0f}% similar. Check by eye.")
    return Result(name, MISMATCH, expected, "(not found)", "Not found on the label.")


def _number_field(name, expected_val, found_val, expected_raw, unit, tol) -> Result:
    if expected_val is None:
        return Result(name, REVIEW, expected_raw, "-", "Could not read the application value.")
    if found_val is None:
        return Result(name, MISMATCH, expected_raw, "(not found)", "Not found on the label.")
    ok = abs(expected_val - found_val) <= tol
    return Result(name, MATCH if ok else MISMATCH, expected_raw,
                  f"{found_val:g} {unit}", "" if ok else f"Label shows {found_val:g} {unit}.")


def compare_label(app: dict, ocr_text: str) -> list[Result]:
    return [
        _text_field("Brand name", app["brand"], ocr_text),
        _text_field("Class/type", app["class_type"], ocr_text),
        _number_field("Alcohol content", parse_abv(app["abv"]), parse_abv(ocr_text),
                      app["abv"], "% ABV", 0.05),
        _number_field("Net contents", parse_volume_ml(app["volume"]), parse_volume_ml(ocr_text),
                      app["volume"], "mL", 1.0),
    ]
