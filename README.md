# Label Check (prototype)

Compares application data to an alcohol label image using local OCR (no cloud calls).

## Setup
1. Install Tesseract: `sudo apt install tesseract-ocr` (Windows/Mac: see the Tesseract docs).
2. `python -m venv venv && source venv/bin/activate`
3. `pip install -r requirements.txt`
4. `streamlit run app.py`

## How it works
- `ocr.py`: grayscale, contrast boost, denoise, deskew, then Tesseract.
- `compare.py`: brand/class use normalized + fuzzy matching; ABV and volume are parsed to numbers.
- `warning.py`: header must be exact caps; body compared to the required wording.
- Results: Match / Needs Review / Mismatch.

## Batch mode
Use the **Many labels** tab: download the CSV template, fill one row per label, upload it with the images, and download the results CSV. Labels are checked 4 at a time (`workers` in `batch.py`).

## Known limits
- Bold detection of the warning header is not implemented (flagged for manual check).
- Glare and extreme angles may still defeat OCR.
- Batch: results depend on the filename in your CSV matching the image file name exactly (case-insensitive).
