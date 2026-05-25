import os
import tempfile
import fitz  # PyMuPDF
import easyocr
import numpy as np
from PIL import Image


def save_uploaded_pdf_temporarily(uploaded_file) -> str:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract selectable/readable text using PyMuPDF.
    """
    text_parts = []

    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        page_text = page.get_text("text")

        if page_text and page_text.strip():
            text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")

    doc.close()

    return "\n".join(text_parts).strip()


def extract_text_from_pdf_ocr(pdf_path: str) -> str:
    """
    OCR fallback using PyMuPDF + EasyOCR.
    No Tesseract or Poppler required.
    """
    reader = easyocr.Reader(["en"], gpu=False)

    ocr_text_parts = []

    doc = fitz.open(pdf_path)

    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

        image = Image.frombytes(
            "RGB",
            [pix.width, pix.height],
            pix.samples
        )

        image_array = np.array(image)

        results = reader.readtext(
            image_array,
            detail=0,
            paragraph=True
        )

        page_text = "\n".join(results)

        if page_text.strip():
            ocr_text_parts.append(f"\n--- Page {page_num} ---\n{page_text}")

    doc.close()

    return "\n".join(ocr_text_parts).strip()


def create_extracted_item_from_pdf(uploaded_file) -> dict:
    """
    Same extracted_item pattern used by web, txt, and youtube ingestion.
    """

    pdf_path = save_uploaded_pdf_temporarily(uploaded_file)

    try:
        extracted_text = extract_text_from_pdf(pdf_path)
        extraction_method = "pymupdf_text_extraction"

        if not extracted_text or len(extracted_text.strip()) < 100:
            extracted_text = extract_text_from_pdf_ocr(pdf_path)
            extraction_method = "easyocr_pdf_ocr_extraction"

        if not extracted_text:
            raise ValueError("No readable text found in PDF, even after OCR.")

        return {
            "title": uploaded_file.name,
            "url": uploaded_file.name,
            "snippet": "PDF uploaded document content",
            "content": extracted_text,
            "extraction_method": extraction_method,
            "source_type": "pdf_file",
            "file_name": uploaded_file.name,
        }

    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)