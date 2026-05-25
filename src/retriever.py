from typing import List, Dict, Any


def retrieve_relevant_chunks(
    vector_store,
    question: str,
    k: int = 5
):
    """
    Retrieve top-k relevant chunks from FAISS vector store.
    """

    if vector_store is None:
        raise ValueError("Vector store is not loaded.")

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    retrieved_docs = vector_store.similarity_search_with_score(
        query=question,
        k=k
    )

    results = []

    for rank, (doc, score) in enumerate(retrieved_docs, start=1):
        results.append({
            "rank": rank,
            "score": float(score),
            "content": doc.page_content,
            "metadata": doc.metadata,
            "title": doc.metadata.get("title", ""),
            "url": doc.metadata.get("url", ""),
            "extraction_method": doc.metadata.get("extraction_method", "")
        })

    return results


def format_retrieved_chunks_for_display(
    retrieved_chunks: List[Dict[str, Any]]
):
    """
    Convert retrieved chunks into a simple display-friendly format.
    """

    display_rows = []

    for item in retrieved_chunks:
        display_rows.append({
            "rank": item["rank"],
            "score": item["score"],
            "title": item["title"],
            "url": item["url"],
            "content_preview": item["content"][:500]
        })

    return display_rows