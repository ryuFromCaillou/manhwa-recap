from __future__ import annotations

from pathlib import Path

from PIL import Image

from .schemas import OCRResult


def run_ocr(chunk_image_path: Path) -> OCRResult:
    """
    Thin wrapper around pytesseract.

    Raises a helpful error if pytesseract (or the Tesseract binary) is not available.

    Args:
        chunk_image_path: Path to a stitched chunk image.

    Returns:
        OCRResult containing raw extracted text and optional average confidence.
    """
    try:
        import pytesseract  # type: ignore
    except Exception as e:  # pragma: no cover
        raise RuntimeError(
            "OCR requested but pytesseract is not installed. Install with: pip install -e '.[ocr]'"
        ) from e

    chunk_id = chunk_image_path.stem
    img = Image.open(chunk_image_path)
    img.load()

    text = pytesseract.image_to_string(img)

    confidence: float | None = None
    try:
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        confs = []
        for c in data.get("conf", []):
            try:
                ci = float(c)
            except Exception:
                continue
            if ci >= 0:
                confs.append(ci)
        if confs:
            confidence = sum(confs) / float(len(confs))
    except Exception:
        confidence = None

    return OCRResult(chunk_id=chunk_id, text=text.strip(), confidence=confidence)
