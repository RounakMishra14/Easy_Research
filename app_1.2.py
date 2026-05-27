import asyncio
import html
import re
import uuid
from datetime import datetime
from urllib.parse import urlparse

import streamlit as st

from src.config import SERPER_API_KEY
from src.serper_search import search_serper
from src.web_extractor import extract_content
from src.document_processor import process_extracted_content

from src.history_manager import (
    create_topic_folder,
    save_metadata,
    list_research_history,
)

from src.vector_store import (
    create_and_save_vector_store,
    load_vector_store,
)

from src.retriever import retrieve_relevant_chunks
from src.answer_generator import generate_answer_from_chunks

from src.file_ingestor import create_extracted_item_from_file
from src.youtube_loader import create_extracted_item_from_youtube
from src.pdf_loader import create_extracted_item_from_pdf


# =====================================================
# PAGE CONFIG
# =====================================================

st.set_page_config(
    page_title="Easy Answer - Multi Source RAG",
    page_icon="🧠",
    layout="wide",
)


# =====================================================
# SESSION DEFAULTS
# =====================================================

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0

if "db_mode_selected" not in st.session_state:
    st.session_state["db_mode_selected"] = False

if "active_db_name" not in st.session_state:
    st.session_state["active_db_name"] = None

if "active_topic_folder" not in st.session_state:
    st.session_state["active_topic_folder"] = None

if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

if "all_chunks" not in st.session_state:
    st.session_state["all_chunks"] = []

if "successful_documents" not in st.session_state:
    st.session_state["successful_documents"] = []


# =====================================================
# HELPERS
# =====================================================

def widget_key(name: str) -> str:
    return f"{name}_{st.session_state['reset_counter']}"


def is_youtube_url(url: str) -> bool:
    lower_url = url.lower()
    return "youtube.com" in lower_url or "youtu.be" in lower_url


def is_url(text: str) -> bool:
    try:
        parsed = urlparse(text)
        return parsed.scheme in ["http", "https"] and bool(parsed.netloc)
    except Exception:
        return False


def extract_urls_and_queries(source_input: str):
    """
    Allows the user to paste mixed input in one box:
    - normal Google search text
    - one or multiple website URLs
    - YouTube URLs

    URLs can be pasted line by line, comma separated, or mixed inside text.
    """
    if not source_input:
        return [], ""

    url_pattern = r"https?://[^\s,]+"
    urls = re.findall(url_pattern, source_input)

    # Remove URLs from remaining text so only natural language search query remains.
    query_text = re.sub(url_pattern, " ", source_input)
    query_lines = [line.strip(" ,") for line in query_text.splitlines() if line.strip(" ,")]
    google_query = " ".join(query_lines).strip()

    # Keep URL order but remove duplicates.
    seen = set()
    clean_urls = []
    for url in urls:
        clean_url = url.strip().rstrip(").,]")
        if clean_url and clean_url not in seen and is_url(clean_url):
            clean_urls.append(clean_url)
            seen.add(clean_url)

    return clean_urls, google_query


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
        dataset_id=dataset_id,
    )

    extracted_item["source_id"] = source_id
    extracted_item["source_type"] = source_type
    extracted_item["dataset_id"] = dataset_id

    return chunks, extracted_item


def safe_history_sort_key(item):
    """Sort latest databases first without crashing on older metadata."""
    candidates = [
        item.get("updated_at"),
        item.get("created_at"),
        item.get("topic", "").split("|")[-1].strip(),
    ]

    formats = [
        "%Y-%m-%d %H:%M:%S",
        "%d.%m.%Y - %I:%M %p",
        "%Y_%m_%d_%H_%M_%S",
    ]

    for value in candidates:
        if not value:
            continue
        for fmt in formats:
            try:
                return datetime.strptime(value, fmt)
            except Exception:
                pass

    return datetime.min


def get_sorted_history():
    history = list_research_history()
    return sorted(history, key=safe_history_sort_key, reverse=True)


def reset_loaded_data():
    keys_to_clear = [
        "all_chunks",
        "successful_documents",
        "query",
        "dataset_id",
        "vector_store",
        "selected_history",
        "retrieved_chunks",
        "active_topic_folder",
        "active_db_name",
        "db_mode_selected",
        "qa_history",
        "source_input_value",
    ]

    widget_prefixes_to_clear = [
        "research_name",
        "source_input",
        "google_num_results",
        "file_uploader",
        "answer_question",
        "answer_top_k",
        "load_data_btn",
        "clear_current_session_btn",
        "generate_answer_btn",
    ]

    for key in list(st.session_state.keys()):
        if key in keys_to_clear or any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["reset_counter"] += 1


def reset_input_fields_only():
    widget_prefixes_to_clear = [
        "source_input",
        "google_num_results",
        "file_uploader",
    ]

    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["reset_counter"] += 1


def render_chat_card(question, answer, time_text):
    safe_question = html.escape(question or "")
    safe_answer = html.escape(answer or "").replace("\n", "<br>")
    safe_time = html.escape(time_text or "")

    st.markdown(
        f"""
        <div class="chat-card">
            <div class="question">Q: {safe_question}</div>
            <div class="answer">{safe_answer}</div>
            <div class="time">{safe_time}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown(
    """
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 6px;
}

.subtitle {
    color: #8a8f98;
    font-size: 16px;
    margin-bottom: 24px;
}

.db-pill {
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: #1f6f43;
    color: white;
    font-size: 14px;
    margin-bottom: 20px;
}

.warning-pill {
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: #8a5a10;
    color: white;
    font-size: 14px;
    margin-bottom: 20px;
}

.chat-card {
    border: 1px solid rgba(120, 120, 120, 0.25);
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 16px;
    background-color: rgba(120, 120, 120, 0.08);
}

.question {
    font-weight: 700;
    font-size: 17px;
    margin-bottom: 8px;
}

.answer {
    color: inherit;
    font-size: 15px;
    line-height: 1.6;
}

.time {
    color: #8a8f98;
    font-size: 12px;
    margin-top: 10px;
}

.small-muted {
    color: #8a8f98;
    font-size: 13px;
}

section[data-testid="stSidebar"] .stButton button {
    width: 100%;
}
</style>
""",
    unsafe_allow_html=True,
)


# =====================================================
# DATABASE STARTUP SCREEN
# =====================================================

history = get_sorted_history()

if not st.session_state["db_mode_selected"]:
    st.markdown('<div class="main-title">🧠 Easy Answer</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="subtitle">Create or select a research database before loading sources.</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        db_choice = st.radio(
            "What do you want to do?",
            ["Create New Database", "Use Existing Database"],
            horizontal=True,
            key=widget_key("db_choice"),
        )

        if db_choice == "Create New Database":
            new_db_name = st.text_input(
                "Enter new database name",
                value="combined_research_db",
                key=widget_key("new_db_name"),
            )

            if st.button("Create Database", use_container_width=True, key=widget_key("create_db_btn")):
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
                st.session_state["qa_history"] = []

                st.rerun()

        else:
            if not history:
                st.info("No existing databases found. Please create a new one.")
                st.stop()

            selected_existing_db = st.selectbox(
                "Choose existing database",
                options=history,
                format_func=lambda x: f"{x.get('topic', '')} | Sources: {x.get('total_sources', 0)} | Chunks: {x.get('total_chunks', 0)}",
                key=widget_key("startup_existing_db"),
            )

            if st.button("Use Selected Database", use_container_width=True, key=widget_key("use_existing_db_btn")):
                with st.spinner("Loading selected database..."):
                    vector_store = load_vector_store(selected_existing_db["folder_path"])

                st.session_state["db_mode_selected"] = True
                st.session_state["active_db_name"] = selected_existing_db["topic"]
                st.session_state["query"] = selected_existing_db["topic"]
                st.session_state["active_topic_folder"] = selected_existing_db["folder_path"]
                st.session_state["vector_store"] = vector_store
                st.session_state["qa_history"] = []

                st.rerun()

    st.stop()


# =========================
# SIDEBAR MODEL SETTINGS
# =========================

st.sidebar.markdown("### 🤖 Model Settings")

llm_provider = st.sidebar.selectbox(
    "Choose LLM Provider",
    ["gemini", "groq", "ollama"],
    index=0,
    key="llm_provider"
)

st.sidebar.divider()

# =====================================================
# SIDEBAR HISTORY
# =====================================================

st.sidebar.header("Research History")

if st.session_state.get("active_db_name"):
    st.sidebar.success("Active Database")
    st.sidebar.write(st.session_state["active_db_name"])

history = get_sorted_history()

if history:
    selected_history = st.sidebar.selectbox(
        "History",
        options=history,
        format_func=lambda x: f"{x.get('topic', '')} | Sources: {x.get('total_sources', 0)}",
        key=widget_key("selected_history_dropdown"),
    )

    if st.sidebar.button("Switch Database", key=widget_key("switch_db_btn")):
        with st.spinner("Switching database..."):
            vector_store = load_vector_store(selected_history["folder_path"])

        st.session_state["vector_store"] = vector_store
        st.session_state["selected_history"] = selected_history
        st.session_state["query"] = selected_history["topic"]
        st.session_state["active_db_name"] = selected_history["topic"]
        st.session_state["active_topic_folder"] = selected_history["folder_path"]
        st.session_state["qa_history"] = []

        st.rerun()
else:
    st.sidebar.info("No previous research history found.")

st.sidebar.divider()

if st.sidebar.button("Clear Current Session", key=widget_key("clear_current_session_btn")):
    reset_loaded_data()
    st.rerun()


# =====================================================
# HEADER
# =====================================================

st.markdown('<div class="main-title">🧠 Easy Answer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Search Google, paste URLs, add PDFs/TXT files, and ask questions from one research database.</div>',
    unsafe_allow_html=True,
)

if st.session_state.get("active_db_name"):
    st.markdown(
        f'<div class="db-pill">Active DB: {html.escape(st.session_state["active_db_name"])}</div>',
        unsafe_allow_html=True,
    )
else:
    st.markdown('<div class="warning-pill">No active DB selected</div>', unsafe_allow_html=True)

if not SERPER_API_KEY:
    st.warning("Google search is disabled because SERPER_API_KEY is missing. URLs and files can still be loaded.")

if st.session_state.get("load_success_message"):
    st.success(st.session_state.pop("load_success_message"))


# =====================================================
# DATA EXTRACT COMPOSER
# =====================================================

st.markdown("### Add Data")

with st.container(border=True):
    research_name = st.text_input(
        "Research database name",
        value=st.session_state.get("query", "combined_research_db"),
        disabled=True,
        key=widget_key("research_name"),
    )

    source_input = st.text_area(
        "Search topic or paste URLs",
        placeholder=(
            "Example:\n"
            "latest AI agents in healthcare\n\n"
            "https://example.com/article\n"
            "https://youtube.com/watch?v=xxxx\n\n"
            "You can paste multiple URLs and one search query together."
        ),
        height=180,
        key=widget_key("source_input"),
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        uploaded_files = st.file_uploader(
            "➕ Add TXT / PDF",
            type=["txt", "pdf"],
            accept_multiple_files=True,
            key=widget_key("file_uploader"),
        )

    with col2:
        google_num_results = st.number_input(
            "Web pages",
            min_value=1,
            max_value=50,
            value=5,
            step=1,
            key=widget_key("google_num_results"),
        )

    with col3:
        st.write("")
        st.write("")
        load_clicked = st.button("Load Data", use_container_width=True, key=widget_key("load_data_btn"))


# =====================================================
# LOAD DATA PIPELINE
# =====================================================

if load_clicked:
    if not research_name.strip():
        st.warning("Please enter a research database name.")
        st.stop()

    manual_urls, google_topic = extract_urls_and_queries(source_input)
    uploaded_files = uploaded_files or []

    has_google_topic = bool(google_topic.strip())
    has_urls = bool(manual_urls)
    has_files = bool(uploaded_files)

    if not has_google_topic and not has_urls and not has_files:
        st.warning("Please provide at least one source: search text, URL, YouTube URL, TXT, or PDF.")
        st.stop()

    dataset_id = st.session_state.get("dataset_id")

    if not dataset_id:
        dataset_id = str(uuid.uuid4())[:8]
        st.session_state["dataset_id"] = dataset_id

    final_db_name = st.session_state.get("active_db_name")

    if not final_db_name:
        current_time = datetime.now().strftime("%d.%m.%Y - %I:%M %p")
        final_db_name = f"{research_name.strip()} | {current_time}"
        st.session_state["active_db_name"] = final_db_name
        st.session_state["query"] = final_db_name

    new_chunks = []
    new_successful_documents = []

    total_items = 1
    if has_google_topic:
        total_items += int(google_num_results)
    total_items += len(manual_urls)
    total_items += len(uploaded_files)

    completed_items = 0
    progress_bar = st.progress(0)
    status_text = st.empty()

    def update_progress(message, completed):
        completed += 1
        progress = min(completed / total_items, 1.0)
        status_text.info(message)
        progress_bar.progress(progress)
        return completed

    # -------------------------
    # GOOGLE SEARCH EXTRACTION
    # -------------------------
    if has_google_topic:
        if not SERPER_API_KEY:
            st.error("SERPER_API_KEY is missing. Google search cannot run.")
            st.stop()

        try:
            status_text.info("Searching Google...")
            search_results = search_serper(google_topic.strip(), int(google_num_results))

            for idx, result in enumerate(search_results, start=1):
                try:
                    status_text.info(f"Extracting Google page {idx}...")

                    extracted_item = asyncio.run(
                        extract_content(
                            url=result["link"],
                            title=result.get("title", f"Google Result {idx}"),
                            snippet=result.get("snippet", ""),
                        )
                    )

                    if extracted_item.get("content"):
                        chunks, processed_item = process_single_extracted_item(
                            extracted_item=extracted_item,
                            source_type="google_search",
                            dataset_id=dataset_id,
                        )
                        new_chunks.extend(chunks)
                        new_successful_documents.append(processed_item)

                    completed_items = update_progress(f"Google page {idx} processed.", completed_items)

                except Exception as e:
                    completed_items = update_progress(f"Skipped Google page {idx}: {type(e).__name__}", completed_items)

        except Exception as e:
            st.error(f"Google search failed: {e}")
            st.stop()

    # -------------------------
    # MANUAL URL / YOUTUBE
    # -------------------------
    for idx, url in enumerate(manual_urls, start=1):
        try:
            if is_youtube_url(url):
                status_text.info(f"Processing YouTube URL {idx}...")
                extracted_item = create_extracted_item_from_youtube(url)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="youtube_url",
                    dataset_id=dataset_id,
                )

            else:
                status_text.info(f"Processing website URL {idx}...")
                extracted_item = asyncio.run(
                    extract_content(
                        url=url,
                        title=f"User Provided URL {idx}",
                        snippet="User provided URL",
                    )
                )

                if not extracted_item.get("content"):
                    completed_items = update_progress(f"Skipped URL {idx}. No extractable content found.", completed_items)
                    continue

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="manual_url",
                    dataset_id=dataset_id,
                )

            new_chunks.extend(chunks)
            new_successful_documents.append(processed_item)
            completed_items = update_progress(f"URL {idx} processed.", completed_items)

        except Exception as e:
            completed_items = update_progress(f"Skipped URL {idx}: {type(e).__name__}", completed_items)

    # -------------------------
    # FILE EXTRACTION
    # -------------------------
    for idx, uploaded_file in enumerate(uploaded_files, start=1):
        try:
            file_name = uploaded_file.name.lower()

            if file_name.endswith(".txt"):
                status_text.info(f"Processing TXT file {idx}...")
                extracted_item = create_extracted_item_from_file(uploaded_file)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="txt_file",
                    dataset_id=dataset_id,
                )

            elif file_name.endswith(".pdf"):
                status_text.info(f"Processing PDF file {idx}...")
                extracted_item = create_extracted_item_from_pdf(uploaded_file)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="pdf_file",
                    dataset_id=dataset_id,
                )

            else:
                completed_items = update_progress(f"Skipped unsupported file {idx}.", completed_items)
                continue

            new_chunks.extend(chunks)
            new_successful_documents.append(processed_item)
            completed_items = update_progress(f"File {idx} processed.", completed_items)

        except Exception as e:
            completed_items = update_progress(f"Skipped file {idx}: {type(e).__name__}", completed_items)

    if not new_chunks:
        progress_bar.empty()
        status_text.empty()
        st.error("No usable content was extracted.")
        st.stop()

    # -------------------------
    # CREATE OR UPDATE VECTOR DB
    # -------------------------
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
                vector_store = create_and_save_vector_store(chunks=all_chunks_for_store, save_path=topic_folder)
        except Exception:
            all_chunks_for_store = existing_chunks + new_chunks
            vector_store = create_and_save_vector_store(chunks=all_chunks_for_store, save_path=topic_folder)
    else:
        topic_folder = create_topic_folder(final_db_name)
        st.session_state["active_topic_folder"] = topic_folder
        vector_store = create_and_save_vector_store(chunks=new_chunks, save_path=topic_folder)

    all_chunks = existing_chunks + new_chunks
    all_successful_documents = existing_documents + new_successful_documents

    now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    metadata = {
        "topic": final_db_name,
        "dataset_id": dataset_id,
        "created_at": st.session_state.get("created_at", now_text),
        "updated_at": now_text,
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
                "extraction_method": doc.get("extraction_method"),
            }
            for doc in all_successful_documents
        ],
    }

    save_metadata(topic_folder, metadata)

    st.session_state["all_chunks"] = all_chunks
    st.session_state["successful_documents"] = all_successful_documents
    st.session_state["query"] = final_db_name
    st.session_state["dataset_id"] = dataset_id
    st.session_state["vector_store"] = vector_store
    st.session_state["active_topic_folder"] = topic_folder
    st.session_state["active_db_name"] = final_db_name
    st.session_state["created_at"] = metadata["created_at"]

    progress_bar.progress(1.0)
    status_text.success("Research database updated successfully.")

    st.session_state["load_success_message"] = (
        f"Database ready. New sources added: {len(new_successful_documents)}. "
        f"Total sources in current DB: {len(all_successful_documents)}."
    )

    reset_input_fields_only()
    st.rerun()



# =====================================================
# ASK QUESTION COMPOSER
# =====================================================

if "vector_store" in st.session_state:
    st.markdown("### Ask from Research Database")

    with st.container(border=True):
        answer_question = st.text_input(
            "Ask a question",
            placeholder="Ask anything from your loaded research database...",
            key=widget_key("answer_question"),
        )

        col_a, col_b = st.columns([1, 1])

        with col_a:
            answer_top_k = st.number_input(
                "Chunks to consider",
                min_value=1,
                max_value=50,
                value=5,
                step=1,
                key=widget_key("answer_top_k"),
            )

        with col_b:
            st.write("")
            st.write("")
            ask_clicked = st.button("Generate Answer", use_container_width=True, key=widget_key("generate_answer_btn"))

    if ask_clicked:
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
            k=int(answer_top_k),
        )

        status_text.info("Generating answer...")
        progress_bar.progress(80)

        final_answer = generate_answer_from_chunks(
            question=answer_question,
            retrieved_chunks=retrieved_chunks,
            provider=st.session_state["llm_provider"]
        )

        progress_bar.progress(100)
        status_text.success("Answer generated.")

        st.session_state["qa_history"].append(
            {
                "question": answer_question,
                "answer": final_answer,
                "time": datetime.now().strftime("%d.%m.%Y - %I:%M %p"),
            }
        )

        st.rerun()
else:
    st.info("Load data first, or switch to an existing database, to enable question answering.")


# =====================================================
# QUESTION / ANSWER HISTORY
# =====================================================

st.divider()
st.markdown("### Conversation History")

if st.session_state.get("qa_history"):
    for item in reversed(st.session_state["qa_history"]):
        render_chat_card(
            question=item.get("question", ""),
            answer=item.get("answer", ""),
            time_text=item.get("time", ""),
        )
else:
    st.caption("No questions asked yet. Your generated answers will appear here so you can scroll back anytime.")



