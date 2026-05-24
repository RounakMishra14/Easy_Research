import os
import pandas as pd


def get_embedding_debug_dataframe(chunks, embeddings_model):
    """
    Generate FULL embedding debug dataframe.
    Each embedding dimension becomes its own column.
    """

    rows = []

    for idx, chunk in enumerate(chunks, start=1):

        text = chunk.page_content

        embedding_vector = embeddings_model.embed_query(text)

        row = {
            "chunk_no": idx,
            "character_count": len(text),
            "embedding_dimension": len(embedding_vector),
            "metadata_title": chunk.metadata.get("title", ""),
            "metadata_url": chunk.metadata.get("url", ""),
            "metadata_extraction_method": chunk.metadata.get("extraction_method", ""),
            "chunk_preview": text[:500]
        }

        # Store every embedding dimension separately
        for dim_idx, value in enumerate(embedding_vector):
            row[f"embedding_{dim_idx}"] = value

        rows.append(row)

    return pd.DataFrame(rows)


def save_embedding_debug_csv(
    chunks,
    embeddings_model,
    save_folder: str,
    filename: str = "embedding_debug_full.csv"
):
    """
    Save full embedding debug CSV inside topic history folder.
    """

    debug_df = get_embedding_debug_dataframe(
        chunks=chunks,
        embeddings_model=embeddings_model
    )

    os.makedirs(save_folder, exist_ok=True)

    csv_path = os.path.join(save_folder, filename)

    debug_df.to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig"
    )

    return csv_path, debug_df