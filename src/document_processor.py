from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def create_document(extracted_item: dict):
    content = extracted_item.get("content")

    if not content:
        return None

    metadata = {
        "title": extracted_item.get("title"),
        "url": extracted_item.get("url"),
        "snippet": extracted_item.get("snippet"),
        "extraction_method": extracted_item.get("extraction_method"),
        "source_type": "web"
    }

    return Document(
        page_content=content,
        metadata=metadata
    )


def chunk_document(
    document: Document,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap
    )

    return text_splitter.split_documents([document])


def process_extracted_content(extracted_item: dict):
    document = create_document(extracted_item)

    if not document:
        return []

    return chunk_document(document)