import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS


EMBEDDING_MODEL_NAME = "BAAI/bge-base-en-v1.5"


def get_embedding_model():
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL_NAME,
        model_kwargs={
            "device": "cpu"
        },
        encode_kwargs={
            "normalize_embeddings": True
        }
    )

    return embeddings


def create_and_save_vector_store(chunks, save_path: str):
    if not chunks:
        raise ValueError("No chunks found. Cannot create vector store.")

    embeddings = get_embedding_model()

    vector_store = FAISS.from_documents(
        documents=chunks,
        embedding=embeddings
    )

    os.makedirs(save_path, exist_ok=True)

    vector_store.save_local(save_path)

    return vector_store


def load_vector_store(save_path: str):
    embeddings = get_embedding_model()

    vector_store = FAISS.load_local(
        folder_path=save_path,
        embeddings=embeddings,
        allow_dangerous_deserialization=True
    )

    return vector_store