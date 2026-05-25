from typing import Dict, Any


def read_txt_file(uploaded_file) -> str:
    """
    Read uploaded TXT file content safely.
    """

    try:
        text = uploaded_file.read().decode("utf-8", errors="ignore")
        return text.strip()

    except Exception as e:
        raise RuntimeError(f"Failed to read TXT file: {e}")


def create_extracted_item_from_txt(uploaded_file) -> Dict[str, Any]:
    """
    Convert uploaded TXT file into the same extracted_item format
    used by web_extractor.py.

    This lets us reuse:
    - process_extracted_content()
    - create_and_save_vector_store()
    - retrieve_relevant_chunks()
    - generate_answer_from_chunks()
    """

    content = read_txt_file(uploaded_file)

    if not content:
        raise ValueError("Uploaded TXT file is empty.")

    extracted_item = {
        "title": uploaded_file.name,
        "url": uploaded_file.name,
        "snippet": "Uploaded TXT file",
        "content": content,
        "extraction_method": "txt_upload",
        "source_type": "txt_file"
    }

    return extracted_item


def create_extracted_item_from_file(uploaded_file) -> Dict[str, Any]:
    """
    Main file ingestion router.

    Future support can be added here:
    - PDF
    - DOCX
    - CSV
    - XLSX
    """

    file_name = uploaded_file.name.lower()

    if file_name.endswith(".txt"):
        return create_extracted_item_from_txt(uploaded_file)

    raise ValueError(
        f"Unsupported file type for now: {uploaded_file.name}"
    )