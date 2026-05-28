import os
import json
from datetime import datetime


CHAT_HISTORY_FILE = "chat_history.json"


def get_chat_history_path(folder_path: str) -> str:
    return os.path.join(folder_path, CHAT_HISTORY_FILE)


def load_chat_history(folder_path: str) -> list:
    if not folder_path:
        return []

    history_path = get_chat_history_path(folder_path)

    if not os.path.exists(history_path):
        return []

    try:
        with open(history_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_chat_history(folder_path: str, chat_history: list):
    if not folder_path:
        return

    os.makedirs(folder_path, exist_ok=True)

    history_path = get_chat_history_path(folder_path)

    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(chat_history, f, indent=4, ensure_ascii=False)


def append_chat_message(folder_path: str, question: str, answer: str) -> list:
    chat_history = load_chat_history(folder_path)

    chat_history.append({
        "question": question,
        "answer": answer,
        "time": datetime.now().strftime("%d.%m.%Y - %I:%M %p"),
    })

    save_chat_history(folder_path, chat_history)

    return chat_history


def clear_chat_history(folder_path: str):
    save_chat_history(folder_path, [])