"""Image preprocessing + local OCR (no network calls)."""
import cv2
import numpy as np
import pytesseract
from PIL import Image


def _deskew(gray: np.ndarray) -> np.ndarray:
    """Straighten small rotations (up to ~15 degrees) using text pixel angles."""
    inv = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
    coords = np.column_stack(np.where(inv > 0))
    if len(coords) < 100:
        return gray
    angle = cv2.minAreaRect(coords.astype(np.float32))[-1]
    angle = -(90 + angle) if angle < -45 else -angle
    if abs(angle) < 0.5 or abs(angle) > 15:
        return gray
    h, w = gray.shape
    m = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(gray, m, (w, h), flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


def preprocess(img: Image.Image, max_side: int = 2000) -> np.ndarray:
    """Grayscale -> resize -> contrast boost -> denoise -> deskew."""
    gray = cv2.cvtColor(np.array(img.convert("RGB")), cv2.COLOR_RGB2GRAY)
    scale = max_side / max(gray.shape)
    if scale < 1 or max(gray.shape) < 1200:  # downscale huge, upscale tiny
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA
                          if scale < 1 else cv2.INTER_CUBIC)
    gray = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)
    gray = cv2.fastNlMeansDenoising(gray, h=10)
    return _deskew(gray)


def extract_text(img: Image.Image) -> str:
    """Return raw OCR text. Case is preserved (the warning check needs it)."""
    # psm 11 = sparse text, which suits labels with scattered text blocks
    return pytesseract.image_to_string(preprocess(img), config="--oem 3 --psm 11")
