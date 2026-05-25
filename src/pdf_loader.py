import os
import tempfile
from pypdf import PdfReader
from pdf2image import convert_from_path
import pytesseract


# Update this path if your Tesseract is installed somewhere else
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract readable/selectable text from PDF.
    """
    text_parts = []

    reader = PdfReader(pdf_path)

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text_parts.append(page_text)

    return "\n".join(text_parts).strip()


def extract_text_from_pdf_ocr(pdf_path: str) -> str:
    """
    OCR fallback for scanned/image-based PDFs.
    """
    ocr_text_parts = []

    pages = convert_from_path(pdf_path, dpi=300)

    for page_number, image in enumerate(pages, start=1):
        text = pytesseract.image_to_string(image)
        if text.strip():
            ocr_text_parts.append(f"\n--- Page {page_number} ---\n{text}")

    return "\n".join(ocr_text_parts).strip()


def save_uploaded_pdf_temporarily(uploaded_file) -> str:
    """
    Save Streamlit uploaded PDF temporarily and return file path.
    """
    suffix = ".pdf"

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
        tmp_file.write(uploaded_file.getbuffer())
        return tmp_file.name


def create_extracted_item_from_pdf(uploaded_file) -> dict:
    """
    Creates extracted_item dictionary similar to web/txt/youtube flow.
    """

    pdf_path = save_uploaded_pdf_temporarily(uploaded_file)

    try:
        extracted_text = extract_text_from_pdf(pdf_path)
        extraction_method = "pdf_text_extraction"

        if not extracted_text or len(extracted_text.strip()) < 100:
            extracted_text = extract_text_from_pdf_ocr(pdf_path)
            extraction_method = "pdf_ocr_extraction"

        if not extracted_text:
            raise ValueError("No readable text found even after OCR.")

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