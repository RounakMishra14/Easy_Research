import os
import re
import json
from datetime import datetime


BASE_VECTOR_DIR = "vector_store"


def slugify_topic(topic: str) -> str:
    topic = topic.lower().strip()
    topic = re.sub(r"[^a-z0-9]+", "_", topic)
    topic = topic.strip("_")
    return topic[:60]


def create_topic_folder(topic: str) -> str:
    timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
    safe_topic = slugify_topic(topic)

    folder_name = f"{safe_topic}_{timestamp}"
    folder_path = os.path.join(BASE_VECTOR_DIR, folder_name)

    os.makedirs(folder_path, exist_ok=True)

    return folder_path


def save_metadata(folder_path: str, metadata: dict):
    metadata_path = os.path.join(folder_path, "metadata.json")

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4, ensure_ascii=False)


def load_metadata(folder_path: str):
    metadata_path = os.path.join(folder_path, "metadata.json")

    if not os.path.exists(metadata_path):
        return {}

    with open(metadata_path, "r", encoding="utf-8") as f:
        return json.load(f)


def list_research_history():
    if not os.path.exists(BASE_VECTOR_DIR):
        return []

    history = []

    for folder in os.listdir(BASE_VECTOR_DIR):
        folder_path = os.path.join(BASE_VECTOR_DIR, folder)

        if os.path.isdir(folder_path):
            metadata = load_metadata(folder_path)

            history.append({
                "folder_name": folder,
                "folder_path": folder_path,
                "topic": metadata.get("topic", folder),
                "created_at": metadata.get("created_at", ""),
                "total_chunks": metadata.get("total_chunks", 0),
                "total_sources": metadata.get("total_sources", 0),
            })

    history = sorted(
        history,
        key=lambda x: x["created_at"],
        reverse=True
    )

    return history