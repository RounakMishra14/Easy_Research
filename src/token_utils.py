from transformers import AutoTokenizer
import pandas as pd


BGE_MODEL_NAME = "BAAI/bge-base-en-v1.5"

tokenizer = AutoTokenizer.from_pretrained(BGE_MODEL_NAME)


def count_tokens(text: str) -> int:
    if not text:
        return 0
    return len(tokenizer.encode(text, add_special_tokens=True))


def get_chunk_token_report(chunks):
    rows = []

    for i, chunk in enumerate(chunks, start=1):
        text = chunk.page_content

        rows.append({
            "chunk_no": i,
            "character_count": len(text),
            "token_count": count_tokens(text),
            "within_512_limit": count_tokens(text) <= 512,
            "title": chunk.metadata.get("title"),
            "url": chunk.metadata.get("url")
        })

    return pd.DataFrame(rows)