"""Batch processing: many label images + one CSV of application data."""
import csv
import io
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image
from ocr import extract_text
from compare import compare_label
from warning import check_warning

ORDER = {"Mismatch": 0, "Needs Review": 1, "Error": 2, "Match": 3}
TEMPLATE = "filename,brand,class_type,abv,volume\nold_tom.jpg,OLD TOM DISTILLERY,Kentucky Straight Bourbon Whiskey,45% Alc./Vol.,750 mL\n"


def overall(statuses: list[str]) -> str:
    return ("Mismatch" if "Mismatch" in statuses
            else "Needs Review" if "Needs Review" in statuses else "Match")


def check_one(name: str, data: bytes, app: dict | None) -> dict:
    """Check a single label. Never raises: failures become an Error row."""
    row = {"File": name}
    if app is None:
        return {**row, "Overall": "Needs Review", "Notes": "No row for this file in the application CSV."}
    try:
        text = extract_text(Image.open(io.BytesIO(data)))
        results = compare_label(app, text)
        w_status, w_msg = check_warning(text)
    except Exception as e:  # unreadable image, OCR failure, etc.
        return {**row, "Overall": "Error", "Notes": f"Could not read image: {e}"}
    notes = [f"{r.field}: {r.note}" for r in results if r.note and r.status != "Match"]
    if w_status != "Match":
        notes.append(f"Warning: {w_msg}")
    return {
        **row,
        "Overall": overall([r.status for r in results] + [w_status]),
        **{r.field: r.status for r in results},
        "Government warning": w_status,
        "Notes": " | ".join(notes),
    }


def parse_applications(csv_text: str) -> dict[str, dict]:
    """Map lowercase filename -> application fields."""
    reader = csv.DictReader(io.StringIO(csv_text.lstrip("\ufeff")))
    return {r["filename"].strip().lower(): {k: (r.get(k) or "").strip()
            for k in ("brand", "class_type", "abv", "volume")}
            for r in reader if r.get("filename")}


def run_batch(files, apps, workers=4, on_progress=None) -> list[dict]:
    """files: [(name, bytes)]. Tesseract runs as a subprocess, so threads give real parallelism."""
    rows = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(check_one, n, d, apps.get(n.lower())) for n, d in files]
        for i, f in enumerate(as_completed(futures), 1):
            rows.append(f.result())
            if on_progress:
                on_progress(i, len(futures))
    return sorted(rows, key=lambda r: (ORDER[r["Overall"]], r["File"]))


def to_csv(rows: list[dict]) -> str:
    cols = ["File", "Overall", "Brand name", "Class/type", "Alcohol content",
            "Net contents", "Government warning", "Notes"]
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue()
