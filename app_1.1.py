import asyncio
import uuid
import json
import os
from datetime import datetime

import streamlit as st

from src.config import SERPER_API_KEY
from src.serper_search import search_serper
from src.web_extractor import extract_content
from src.document_processor import process_extracted_content

from src.history_manager import (
    create_topic_folder,
    save_metadata,
    list_research_history
)

from src.vector_store import (
    create_and_save_vector_store,
    load_vector_store
)

from src.retriever import retrieve_relevant_chunks
from src.answer_generator import generate_answer_from_chunks

from src.file_ingestor import create_extracted_item_from_file
from src.youtube_loader import create_extracted_item_from_youtube
from src.pdf_loader import create_extracted_item_from_pdf


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Easy Answer - Multi Source RAG",
    page_icon="🧠",
    layout="wide"
)

st.title("🧠 Easy Answer - Multi Source Research DB")


# =========================
# RESET / WIDGET KEYS
# =========================

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0


def widget_key(name):
    return f"{name}_{st.session_state['reset_counter']}"


# =========================
# SESSION DEFAULTS
# =========================

if "manual_urls" not in st.session_state:
    st.session_state["manual_urls"] = [""]

if "db_mode_selected" not in st.session_state:
    st.session_state["db_mode_selected"] = False

if "active_db_name" not in st.session_state:
    st.session_state["active_db_name"] = None

if "active_topic_folder" not in st.session_state:
    st.session_state["active_topic_folder"] = None


# =========================
# HELPER FUNCTIONS
# =========================

def is_youtube_url(url):
    return "youtube.com" in url.lower() or "youtu.be" in url.lower()


def add_source_id_to_chunks(chunks, source_id, source_type, dataset_id):
    for chunk in chunks:
        chunk.metadata["source_id"] = source_id
        chunk.metadata["source_type"] = source_type
        chunk.metadata["dataset_id"] = dataset_id
    return chunks


def process_single_extracted_item(extracted_item, source_type, dataset_id):
    source_id = str(uuid.uuid4())[:8]

    chunks = process_extracted_content(extracted_item)

    chunks = add_source_id_to_chunks(
        chunks=chunks,
        source_id=source_id,
        source_type=source_type,
        dataset_id=dataset_id
    )

    extracted_item["source_id"] = source_id
    extracted_item["source_type"] = source_type
    extracted_item["dataset_id"] = dataset_id

    return chunks, extracted_item


def reset_loaded_data():
    keys_to_clear = [
    "all_chunks",
    "successful_documents",
    "query",
    "dataset_id",
    "vector_store",
    "selected_history",
    "retrieved_chunks",
    "manual_urls",
    "active_topic_folder",
    "active_db_name",
    "db_mode_selected",
    ]

    widget_prefixes_to_clear = [
        "research_name",
        "google_topic",
        "google_num_results",
        "manual_url_",
        "file_uploader",
        "answer_question",
        "answer_top_k",
        "load_data_btn",
        "clear_current_session_btn",
        "add_manual_url_btn",
    ]

    for key in list(st.session_state.keys()):
        if key in keys_to_clear or any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["manual_urls"] = [""]
    st.session_state["reset_counter"] += 1


def save_or_update_metadata(topic_folder, metadata):
    save_metadata(topic_folder, metadata)
    
def reset_input_fields_only():
    input_keys_to_clear = [
        "manual_urls",
    ]

    widget_prefixes_to_clear = [
        "google_topic",
        "google_num_results",
        "manual_url_",
        "file_uploader",
    ]

    for key in list(st.session_state.keys()):
        if key in input_keys_to_clear or any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["manual_urls"] = [""]

    # Rebuild only input widgets like file uploader and URL fields
    st.session_state["reset_counter"] += 1

# =========================
# DATABASE STARTUP SCREEN
# =========================

history = list_research_history()
history = sorted(

    history,
    key=lambda x: datetime.strptime(

        #x.get("updated_at", x.get("created_at")),
        #"%Y-%m-%d %H:%M:%S"

        x["topic"].split("|")[-1].strip(),
        "%d.%m.%Y - %I:%M %p"
    ), #if x.get("updated_at", x.get("created_at")) else datetime.min,
    reverse=True
    )

if not st.session_state["db_mode_selected"]:

    st.header("Choose Research Database")

    db_choice = st.radio(
        "What do you want to do?",
        ["Create New Database", "Use Existing Database"],
        key=widget_key("db_choice")
    )

    if db_choice == "Create New Database":

        new_db_name = st.text_input(
            "Enter new database name",
            value="combined_research_db",
            key=widget_key("new_db_name")
        )

        if st.button("Create Database", key=widget_key("create_db_btn")):

            if not new_db_name.strip():
                st.warning("Please enter a database name.")
                st.stop()

            dataset_id = str(uuid.uuid4())[:8]
            current_time = datetime.now().strftime("%d.%m.%Y - %I:%M %p")
            final_db_name = f"{new_db_name.strip()} | {current_time}"

            st.session_state["db_mode_selected"] = True
            st.session_state["active_db_name"] = final_db_name
            st.session_state["query"] = final_db_name
            st.session_state["dataset_id"] = dataset_id
            st.session_state["active_topic_folder"] = None

            st.rerun()

    else:

        if not history:
            st.info("No existing databases found. Please create a new one.")
            st.stop()

        selected_existing_db = st.selectbox(
            "Choose existing database",
            options=history,
            format_func=lambda x: f"{x['topic']} | {x.get('updated_at', x.get('created_at', ''))}",
            key=widget_key("startup_existing_db")
        )

        if st.button("Use Selected Database", key=widget_key("use_existing_db_btn")):

            with st.spinner("Loading selected database..."):
                vector_store = load_vector_store(selected_existing_db["folder_path"])

            st.session_state["db_mode_selected"] = True
            st.session_state["active_db_name"] = selected_existing_db["topic"]
            st.session_state["query"] = selected_existing_db["topic"]
            st.session_state["active_topic_folder"] = selected_existing_db["folder_path"]
            st.session_state["vector_store"] = vector_store

            st.rerun()

    st.stop()


# =========================
# SIDEBAR HISTORY
# =========================


st.sidebar.header("Research History")

if st.session_state.get("active_db_name"):
    st.sidebar.success("Active Database")
    st.sidebar.write(st.session_state["active_db_name"])



history = list_research_history()

history = sorted(
    history,
    key=lambda x: datetime.strptime(
        x["topic"].split("|")[-1].strip(),
        "%d.%m.%Y - %I:%M %p"
    ),
    reverse=True
)

if history:
    selected_history = st.sidebar.selectbox(
        "History",
        options=history,
        format_func=lambda x: f"{x['topic']} | {x.get('updated_at', x.get('created_at', ''))}",
        key=widget_key("selected_history_dropdown")
    )

    if st.sidebar.button("Switch Database", key=widget_key("switch_db_btn")):
        with st.spinner("Switching database..."):
            vector_store = load_vector_store(selected_history["folder_path"])

        st.session_state["vector_store"] = vector_store
        st.session_state["selected_history"] = selected_history
        st.session_state["query"] = selected_history["topic"]
        st.session_state["active_db_name"] = selected_history["topic"]
        st.session_state["active_topic_folder"] = selected_history["folder_path"]

        st.rerun()
else:
    st.sidebar.info("No previous research history found.")
st.sidebar.divider()

if st.sidebar.button("Clear Current Session", key=widget_key("clear_current_session_btn")):
    reset_loaded_data()
    st.sidebar.success("Current session cleared.")
    st.rerun()




# =========================
# INTRO
# =========================

st.write(
    "Add a Google search topic, URLs, or files. Then click **Load Data**. "
    "If a research database is already active, new data will be added to the same database."
)

if not SERPER_API_KEY:
    st.warning("Google search is disabled because SERPER_API_KEY is missing.")


# =========================
# DATA EXTRACT SECTION
# =========================

st.divider()
st.header("Data Extract")

research_name = st.text_input(
    "Research database name",
    value=st.session_state.get("query", "combined_research_db"),
    disabled=True,
    key=widget_key("research_name")
)

google_topic = st.text_input(
    "Google search topic",
    placeholder="Example: latest AI agents",
    key=widget_key("google_topic")
)

google_num_results = st.number_input(
    "Number of websites to extract from Google",
    min_value=1,
    max_value=50,
    value=5,
    step=1,
    key=widget_key("google_num_results")
)

st.subheader("Add URLs")

for i in range(len(st.session_state["manual_urls"])):
    st.session_state["manual_urls"][i] = st.text_input(
        f"URL {i + 1}",
        value=st.session_state["manual_urls"][i],
        placeholder="Paste website or YouTube URL",
        key=widget_key(f"manual_url_{i}")
    )

if st.button("Add More URL", key=widget_key("add_manual_url_btn")):
    st.session_state["manual_urls"].append("")
    st.rerun()

st.subheader("Add TXT / PDF Files")

uploaded_files = st.file_uploader(
    "Upload TXT or PDF files",
    type=["txt", "pdf"],
    accept_multiple_files=True,
    key=widget_key("file_uploader")
)


# =========================
# LOAD DATA BUTTON
# =========================

# removing the CLar data button from the main page to the side bar.

# col1, col2 = st.columns([1, 1])

# with col1:
#     load_clicked = st.button("Load Data")

# with col2:
#     clear_clicked = st.button("Clear Session")

load_clicked = st.button("Load Data", key=widget_key("load_data_btn"))



if load_clicked:

    if not research_name.strip():
        st.warning("Please enter a research database name.")
        st.stop()

    manual_urls = [
        url.strip()
        for url in st.session_state.get("manual_urls", [])
        if url.strip()
    ]

    uploaded_files = uploaded_files or []

    has_google_topic = bool(google_topic.strip())
    has_urls = bool(manual_urls)
    has_files = bool(uploaded_files)

    if not has_google_topic and not has_urls and not has_files:
        st.warning("Please provide at least one source.")
        st.stop()

    dataset_id = st.session_state.get("dataset_id")

    if not dataset_id:
        dataset_id = str(uuid.uuid4())[:8]
        st.session_state["dataset_id"] = dataset_id

    final_db_name = st.session_state.get("active_db_name")

    if not final_db_name:
        current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_db_name = f"{research_name.strip()}_{current_time}"
        st.session_state["active_db_name"] = final_db_name
        st.session_state["query"] = final_db_name

    new_chunks = []
    new_successful_documents = []

    total_items = 0

    if has_google_topic:
        total_items += int(google_num_results)

    total_items += len(manual_urls)
    total_items += len(uploaded_files)
    total_items += 1

    completed_items = 0

    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(message, completed):
        completed += 1
        progress = min(completed / total_items, 1.0)
        status_text.info(message)
        progress_bar.progress(progress)
        return completed

    # =========================
    # GOOGLE SEARCH + EXTRACTION
    # =========================

    if has_google_topic:

        if not SERPER_API_KEY:
            st.error("SERPER_API_KEY is missing. Google search cannot run.")
            st.stop()

        try:
            status_text.info("Searching Google...")

            search_results = search_serper(
                google_topic.strip(),
                int(google_num_results)
            )

            for idx, result in enumerate(search_results, start=1):

                try:
                    status_text.info(f"Extracting Google page {idx}...")

                    extracted_item = asyncio.run(
                        extract_content(
                            url=result["link"],
                            title=result["title"],
                            snippet=result.get("snippet", "")
                        )
                    )

                    if extracted_item.get("content"):
                        chunks, processed_item = process_single_extracted_item(
                            extracted_item=extracted_item,
                            source_type="google_search",
                            dataset_id=dataset_id
                        )

                        new_chunks.extend(chunks)
                        new_successful_documents.append(processed_item)

                    completed_items = update_progress(
                        f"Google page {idx} processed.",
                        completed_items
                    )

                except Exception:
                    completed_items = update_progress(
                        f"Skipped Google page {idx}.",
                        completed_items
                    )

        except Exception as e:
            st.error(f"Google search failed: {e}")
            st.stop()

    # =========================
    # MANUAL URL EXTRACTION
    # =========================

    for idx, url in enumerate(manual_urls, start=1):

        try:
            if is_youtube_url(url):
                status_text.info(f"Processing YouTube URL {idx}...")

                extracted_item = create_extracted_item_from_youtube(url)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="youtube_url",
                    dataset_id=dataset_id
                )

            else:
                status_text.info(f"Processing website URL {idx}...")

                extracted_item = asyncio.run(
                    extract_content(
                        url=url,
                        title=f"User Provided URL {idx}",
                        snippet="User provided URL"
                    )
                )

                if not extracted_item.get("content"):
                    completed_items = update_progress(
                        f"Skipped URL {idx}.",
                        completed_items
                    )
                    continue

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="manual_url",
                    dataset_id=dataset_id
                )

            new_chunks.extend(chunks)
            new_successful_documents.append(processed_item)

            completed_items = update_progress(
                f"URL {idx} processed.",
                completed_items
            )

        except Exception:
            completed_items = update_progress(
                f"Skipped URL {idx}.",
                completed_items
            )

    # =========================
    # FILE EXTRACTION
    # =========================

    for idx, uploaded_file in enumerate(uploaded_files, start=1):

        try:
            file_name = uploaded_file.name.lower()

            if file_name.endswith(".txt"):
                status_text.info(f"Processing TXT file {idx}...")

                extracted_item = create_extracted_item_from_file(uploaded_file)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="txt_file",
                    dataset_id=dataset_id
                )

            elif file_name.endswith(".pdf"):
                status_text.info(f"Processing PDF file {idx}...")

                extracted_item = create_extracted_item_from_pdf(uploaded_file)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="pdf_file",
                    dataset_id=dataset_id
                )

            else:
                completed_items = update_progress(
                    f"Skipped unsupported file {idx}.",
                    completed_items
                )
                continue

            new_chunks.extend(chunks)
            new_successful_documents.append(processed_item)

            completed_items = update_progress(
                f"File {idx} processed.",
                completed_items
            )

        except Exception:
            completed_items = update_progress(
                f"Skipped file {idx}.",
                completed_items
            )

    if not new_chunks:
        progress_bar.empty()
        status_text.empty()
        st.error("No usable content was extracted.")
        st.stop()

    # =========================
    # CREATE OR UPDATE VECTOR DB
    # =========================

    status_text.info("Creating or updating research database...")

    existing_vector_store = st.session_state.get("vector_store")
    existing_chunks = st.session_state.get("all_chunks", [])
    existing_documents = st.session_state.get("successful_documents", [])

    topic_folder = st.session_state.get("active_topic_folder")

    if topic_folder:
        try:
            if existing_vector_store is not None:
                existing_vector_store.add_documents(new_chunks)
                existing_vector_store.save_local(topic_folder)
                vector_store = existing_vector_store
            else:
                all_chunks_for_store = existing_chunks + new_chunks
                vector_store = create_and_save_vector_store(
                    chunks=all_chunks_for_store,
                    save_path=topic_folder
                )

        except Exception:
            all_chunks_for_store = existing_chunks + new_chunks
            vector_store = create_and_save_vector_store(
                chunks=all_chunks_for_store,
                save_path=topic_folder
            )

    else:
        topic_folder = create_topic_folder(final_db_name)
        st.session_state["active_topic_folder"] = topic_folder

        vector_store = create_and_save_vector_store(
            chunks=new_chunks,
            save_path=topic_folder
        )

    all_chunks = existing_chunks + new_chunks
    all_successful_documents = existing_documents + new_successful_documents

    metadata = {
        "topic": final_db_name,
        "dataset_id": dataset_id,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_chunks": len(all_chunks),
        "total_sources": len(all_successful_documents),
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "vector_store_type": "FAISS",
        "storage_path": topic_folder,
        "sources": [
            {
                "source_id": doc.get("source_id"),
                "source_type": doc.get("source_type"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "extraction_method": doc.get("extraction_method")
            }
            for doc in all_successful_documents
        ]
    }

    save_metadata(topic_folder, metadata)

    st.session_state["all_chunks"] = all_chunks
    st.session_state["successful_documents"] = all_successful_documents
    st.session_state["query"] = final_db_name
    st.session_state["dataset_id"] = dataset_id
    st.session_state["vector_store"] = vector_store
    st.session_state["active_topic_folder"] = topic_folder
    st.session_state["active_db_name"] = final_db_name

    progress_bar.progress(1.0)
    status_text.success("Research database updated successfully.")

    st.session_state["load_success_message"] = (
    f"Database ready. New sources added: {len(new_successful_documents)}. "
    f"Total sources in current DB: {len(all_successful_documents)}."
    )

    reset_input_fields_only()

    st.rerun()


# =========================
# ASK QUESTION SECTION
# =========================

if "vector_store" in st.session_state:

    st.divider()
    st.header("Ask from Research Database")

    answer_question = st.text_input(
        "Ask a question",
        key=widget_key("answer_question")
    )

    answer_top_k = st.number_input(
        "Number of chunks to consider before answering",
        min_value=1,
        max_value=50,
        value=5,
        step=1,
        key=widget_key("answer_top_k")
    )

    if st.button("Generate Answer", key=widget_key("generate_answer_btn")):

        if not answer_question.strip():
            st.warning("Please enter a question.")
            st.stop()

        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.info("Retrieving relevant information...")
        progress_bar.progress(40)

        retrieved_chunks = retrieve_relevant_chunks(
            vector_store=st.session_state["vector_store"],
            question=answer_question,
            k=int(answer_top_k)
        )

        status_text.info("Generating answer...")
        progress_bar.progress(80)

        final_answer = generate_answer_from_chunks(
            question=answer_question,
            retrieved_chunks=retrieved_chunks
        )

        progress_bar.progress(100)
        status_text.success("Answer generated.")

        st.subheader("Answer")
        st.write(final_answer)