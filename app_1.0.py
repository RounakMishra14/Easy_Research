import asyncio
import uuid
from datetime import datetime

import streamlit as st

from src.config import SERPER_API_KEY
from src.serper_search import search_serper
from src.web_extractor import extract_content
from src.document_processor import process_extracted_content
from src.embedding_debugger import save_embedding_debug_csv
from src.vector_store import get_embedding_model

from src.history_manager import (
    create_topic_folder,
    save_metadata,
    list_research_history
)

from src.vector_store import (
    create_and_save_vector_store,
    load_vector_store
)

from src.retriever import (
    retrieve_relevant_chunks,
    format_retrieved_chunks_for_display
)

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

st.title("🧠 Easy Answer ")


# =========================
# RESET / WIDGET KEY VERSION
# =========================

if "reset_counter" not in st.session_state:
    st.session_state["reset_counter"] = 0


def widget_key(name):
    return f"{name}_{st.session_state['reset_counter']}"


# =========================
# HELPER FUNCTIONS
# =========================

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
        "youtube_urls",
        "manual_urls",
    ]

    widget_prefixes_to_clear = [
        "research_name",
        "use_web_search",
        "use_txt_files",
        "use_pdf_files",
        "use_youtube",
        "use_manual_urls",
        "web_search_query",
        "web_search_num_results",
        "txt_file_uploader",
        "pdf_file_uploader",
        "youtube_url_",
        "manual_url_",
        "retrieval_question",
        "retrieval_top_k",
        "answer_question",
        "answer_top_k",
    ]

    for key in list(st.session_state.keys()):
        if key in keys_to_clear or any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["youtube_urls"] = [""]
    st.session_state["manual_urls"] = [""]

    # This forces Streamlit to rebuild file uploaders, checkboxes and inputs.
    st.session_state["reset_counter"] += 1


# =========================
# SIDEBAR HISTORY
# =========================

st.sidebar.header("Research History")

history = list_research_history()

if history:
    selected_history = st.sidebar.selectbox(
        "Previous searches",
        options=history,
        format_func=lambda x: f"{x['topic']} | {x['created_at']}"
    )

    if st.sidebar.button("Load Selected Vector DB"):
        vector_store = load_vector_store(selected_history["folder_path"])
        st.session_state["vector_store"] = vector_store
        st.session_state["selected_history"] = selected_history
        st.sidebar.success("Vector DB loaded successfully.")
else:
    st.sidebar.info("No previous research history found.")


# =========================
# APP INTRO
# =========================

st.write(
    "Select one or more input sources, then click **Load Data into Common Research DB**. "
    "All selected data will be processed together and saved into one FAISS vector database."
)

if SERPER_API_KEY:
    st.success("SERPER_API_KEY loaded successfully.")
else:
    st.warning("SERPER_API_KEY not found. Web search will not work unless configured.")


# =========================
# MULTI SOURCE INPUT SECTION
# =========================

st.divider()
st.header("Step 1: Choose Data Sources")

research_name = st.text_input(
    "Enter a name for this research database",
    value="combined_research_db",
    key=widget_key("research_name")
)

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    use_web_search = st.checkbox("Web Search", key=widget_key("use_web_search"))

with col2:
    use_txt_files = st.checkbox("TXT Files", key=widget_key("use_txt_files"))

with col3:
    use_pdf_files = st.checkbox("PDF Files", key=widget_key("use_pdf_files"))

with col4:
    use_youtube = st.checkbox("YouTube URLs", key=widget_key("use_youtube"))

with col5:
    use_manual_urls = st.checkbox("Manual URLs", key=widget_key("use_manual_urls"))


# =========================
# WEB SEARCH INPUT
# =========================

if use_web_search:
    st.subheader("Web Search Input")

    web_query = st.text_input(
        "Enter search query",
        value="latest AI agents",
        key=widget_key("web_search_query")
    )

    num_results = st.slider(
        "Number of search results",
        min_value=1,
        max_value=10,
        value=3,
        key=widget_key("web_search_num_results")
    )
else:
    web_query = ""
    num_results = 0


# =========================
# TXT FILE INPUT
# =========================

if use_txt_files:
    st.subheader("TXT File Input")

    uploaded_txt_files = st.file_uploader(
        "Upload TXT files",
        type=["txt"],
        accept_multiple_files=True,
        key=widget_key("txt_file_uploader")
    )
else:
    uploaded_txt_files = []


# =========================
# PDF FILE INPUT
# =========================

if use_pdf_files:
    st.subheader("PDF File Input")

    uploaded_pdf_files = st.file_uploader(
        "Upload PDF files",
        type=["pdf"],
        accept_multiple_files=True,
        key=widget_key("pdf_file_uploader")
    )
else:
    uploaded_pdf_files = []


# =========================
# YOUTUBE URL INPUT
# =========================

if "youtube_urls" not in st.session_state:
    st.session_state["youtube_urls"] = [""]

if use_youtube:
    st.subheader("YouTube URL Input")

    for i in range(len(st.session_state["youtube_urls"])):
        st.session_state["youtube_urls"][i] = st.text_input(
            f"YouTube URL {i + 1}",
            value=st.session_state["youtube_urls"][i],
            key=widget_key(f"youtube_url_{i}")
        )

    if st.button("Add Another YouTube URL", key=widget_key("add_youtube_url_btn")):
        st.session_state["youtube_urls"].append("")
        st.rerun()


# =========================
# MANUAL URL INPUT
# =========================

if "manual_urls" not in st.session_state:
    st.session_state["manual_urls"] = [""]

if use_manual_urls:
    st.subheader("Manual URL Input")

    for i in range(len(st.session_state["manual_urls"])):
        st.session_state["manual_urls"][i] = st.text_input(
            f"Manual URL {i + 1}",
            value=st.session_state["manual_urls"][i],
            key=widget_key(f"manual_url_{i}")
        )

    if st.button("Add Another Manual URL", key=widget_key("add_manual_url_btn")):
        st.session_state["manual_urls"].append("")
        st.rerun()


# =========================
# COMMON LOAD DATA BUTTON
# =========================

st.divider()
st.header("Step 2: Load Selected Data")

if st.button("Load Data into Common Research DB"):

    if not research_name.strip():
        st.warning("Please enter a research database name.")
        st.stop()

    if not any([
        use_web_search,
        use_txt_files,
        use_pdf_files,
        use_youtube,
        use_manual_urls
    ]):
        st.warning("Please select at least one data source.")
        st.stop()

    dataset_id = str(uuid.uuid4())[:8]

    combined_chunks = []
    successful_documents = []

    st.info(f"Dataset ID: {dataset_id}")

    # =========================
    # PROCESS WEB SEARCH
    # =========================

    if use_web_search:

        if not SERPER_API_KEY:
            st.error("SERPER_API_KEY not found. Web search cannot run.")
            st.stop()

        if not web_query.strip():
            st.warning("Please enter a web search query.")
            st.stop()

        with st.spinner("Searching web using Serper..."):
            search_results = search_serper(web_query, num_results)

        st.subheader("Web Search Results")
        st.write(f"Results returned after filtering: {len(search_results)}")

        for idx, result in enumerate(search_results, start=1):
            st.markdown(f"### Search Result {idx}: {result['title']}")
            st.write(result["link"])
            st.write(result["snippet"])

            with st.spinner(f"Extracting web result {idx}..."):
                extracted_item = asyncio.run(
                    extract_content(
                        url=result["link"],
                        title=result["title"],
                        snippet=result["snippet"]
                    )
                )

            if extracted_item.get("content"):

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="web_search",
                    dataset_id=dataset_id
                )

                combined_chunks.extend(chunks)
                successful_documents.append(processed_item)

                st.success(
                    f"Web result {idx} processed. Chunks created: {len(chunks)}"
                )

            else:
                st.warning(f"Could not extract content from web result {idx}.")

            st.divider()

    # =========================
    # PROCESS TXT FILES
    # =========================

    if use_txt_files:

        if not uploaded_txt_files:
            st.warning("TXT source selected but no TXT files uploaded.")

        for uploaded_file in uploaded_txt_files:

            with st.spinner(f"Processing TXT file: {uploaded_file.name}"):

                extracted_item = create_extracted_item_from_file(uploaded_file)

                chunks, processed_item = process_single_extracted_item(
                    extracted_item=extracted_item,
                    source_type="txt_file",
                    dataset_id=dataset_id
                )

                combined_chunks.extend(chunks)
                successful_documents.append(processed_item)

            st.success(
                f"TXT file processed: {uploaded_file.name}. Chunks created: {len(chunks)}"
            )

    # =========================
    # PROCESS PDF FILES
    # =========================

    if use_pdf_files:

        if not uploaded_pdf_files:
            st.warning("PDF source selected but no PDF files uploaded.")

        for uploaded_pdf in uploaded_pdf_files:

            try:
                with st.spinner(f"Processing PDF file: {uploaded_pdf.name}"):

                    extracted_item = create_extracted_item_from_pdf(uploaded_pdf)

                    chunks, processed_item = process_single_extracted_item(
                        extracted_item=extracted_item,
                        source_type="pdf_file",
                        dataset_id=dataset_id
                    )

                    combined_chunks.extend(chunks)
                    successful_documents.append(processed_item)

                st.success(
                    f"PDF file processed: {uploaded_pdf.name}. Chunks created: {len(chunks)}"
                )

                st.write("PDF extraction method:")
                st.code(extracted_item.get("extraction_method", "unknown"))

            except Exception as e:
                st.error(f"PDF processing failed for {uploaded_pdf.name}: {e}")

    # =========================
    # PROCESS YOUTUBE URLS
    # =========================

    if use_youtube:

        youtube_urls = [
            url.strip()
            for url in st.session_state["youtube_urls"]
            if url.strip()
        ]

        if not youtube_urls:
            st.warning("YouTube source selected but no YouTube URL entered.")

        for idx, youtube_url in enumerate(youtube_urls, start=1):

            try:
                with st.spinner(f"Processing YouTube URL {idx}..."):

                    extracted_item = create_extracted_item_from_youtube(youtube_url)

                    chunks, processed_item = process_single_extracted_item(
                        extracted_item=extracted_item,
                        source_type="youtube",
                        dataset_id=dataset_id
                    )

                    combined_chunks.extend(chunks)
                    successful_documents.append(processed_item)

                st.success(
                    f"YouTube URL {idx} processed. Chunks created: {len(chunks)}"
                )

                st.write("Video ID:")
                st.code(extracted_item.get("video_id", "unknown"))

            except Exception as e:
                st.error(f"YouTube processing failed for URL {idx}: {e}")

    # =========================
    # PROCESS MANUAL URLS
    # =========================

    if use_manual_urls:

        manual_urls = [
            url.strip()
            for url in st.session_state["manual_urls"]
            if url.strip()
        ]

        if not manual_urls:
            st.warning("Manual URL source selected but no URL entered.")

        for idx, url in enumerate(manual_urls, start=1):

            try:
                with st.spinner(f"Processing manual URL {idx}..."):

                    extracted_item = asyncio.run(
                        extract_content(
                            url=url,
                            title=f"Manual URL {idx}",
                            snippet="User provided URL"
                        )
                    )

                if extracted_item.get("content"):

                    chunks, processed_item = process_single_extracted_item(
                        extracted_item=extracted_item,
                        source_type="manual_url",
                        dataset_id=dataset_id
                    )

                    combined_chunks.extend(chunks)
                    successful_documents.append(processed_item)

                    st.success(
                        f"Manual URL {idx} processed. Chunks created: {len(chunks)}"
                    )

                else:
                    st.warning(f"Could not extract content from manual URL {idx}: {url}")

            except Exception as e:
                st.error(f"Manual URL processing failed for URL {idx}: {e}")

    # =========================
    # FINAL SESSION SAVE
    # =========================

    if not combined_chunks:
        st.error("No chunks were created. Please check your selected sources.")
        st.stop()

    final_db_name = f"{research_name.strip()}_{dataset_id}"

    st.session_state["all_chunks"] = combined_chunks
    st.session_state["successful_documents"] = successful_documents
    st.session_state["query"] = final_db_name
    st.session_state["dataset_id"] = dataset_id

    st.success(
        f"Data loading completed. Sources processed: {len(successful_documents)}. "
        f"Total chunks created: {len(combined_chunks)}."
    )

    st.subheader("Loaded Source Summary")

    source_summary = []

    for doc in successful_documents:
        source_summary.append(
            {
                "source_id": doc.get("source_id"),
                "source_type": doc.get("source_type"),
                "title": doc.get("title"),
                "url": doc.get("url"),
                "extraction_method": doc.get("extraction_method")
            }
        )

    st.dataframe(source_summary, use_container_width=True)


# =========================
# CREATE EMBEDDINGS SECTION
# =========================

if "all_chunks" in st.session_state and st.session_state["all_chunks"]:

    st.divider()
    st.header("Step 3: Create and Save Embeddings")

    st.write(f"Current research DB name: `{st.session_state['query']}`")
    st.write(f"Total chunks ready for embedding: {len(st.session_state['all_chunks'])}")
    st.write(f"Total sources: {len(st.session_state['successful_documents'])}")

    if st.button("Create and Save Embeddings"):

        with st.spinner("Creating embeddings and saving FAISS vector store..."):

            topic_folder = create_topic_folder(st.session_state["query"])

            vector_store = create_and_save_vector_store(
                chunks=st.session_state["all_chunks"],
                save_path=topic_folder
            )

            metadata = {
                "topic": st.session_state["query"],
                "dataset_id": st.session_state.get("dataset_id"),
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_chunks": len(st.session_state["all_chunks"]),
                "total_sources": len(st.session_state["successful_documents"]),
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
                    for doc in st.session_state["successful_documents"]
                ]
            }

            save_metadata(topic_folder, metadata)

            st.session_state["vector_store"] = vector_store

            st.success("Embeddings created and saved successfully.")
            st.code(topic_folder)
            st.rerun()


# =========================
# RETRIEVAL TEST SECTION
# =========================

if "vector_store" in st.session_state:

    st.divider()
    st.header("Step 4: Test Retrieval from FAISS")

    retrieval_question = st.text_input(
        "Ask a question to retrieve relevant chunks",
        key=widget_key("retrieval_question")
    )

    retrieval_top_k = st.slider(
        "Number of chunks to retrieve",
        min_value=1,
        max_value=10,
        value=5,
        key=widget_key("retrieval_top_k")
    )

    if st.button("Retrieve Relevant Chunks"):

        if not retrieval_question.strip():
            st.warning("Please enter a question.")
            st.stop()

        retrieved_chunks = retrieve_relevant_chunks(
            vector_store=st.session_state["vector_store"],
            question=retrieval_question,
            k=retrieval_top_k
        )

        st.session_state["retrieved_chunks"] = retrieved_chunks

        display_rows = format_retrieved_chunks_for_display(retrieved_chunks)

        st.subheader("Retrieved Chunks Summary")
        st.dataframe(display_rows, use_container_width=True)

        st.subheader("Detailed Retrieved Chunks")

        for item in retrieved_chunks:
            st.markdown(f"### Rank {item['rank']}")
            st.write(f"Score: {item['score']}")
            st.write(f"Title: {item['title']}")
            st.write(f"URL: {item['url']}")

            if "source_type" in item:
                st.write(f"Source Type: {item['source_type']}")

            if "source_id" in item:
                st.write(f"Source ID: {item['source_id']}")

            st.text_area(
                "Chunk Content",
                item["content"],
                height=250,
                key=f"retrieved_chunk_{item['rank']}"
            )

            st.divider()


# =========================
# ANSWER GENERATION SECTION
# =========================

if "vector_store" in st.session_state:

    st.divider()
    st.header("Step 5: Ask Questions from Research Database")

    answer_question = st.text_input(
        "Ask a question from your research database",
        key=widget_key("answer_question")
    )

    answer_top_k = st.slider(
        "Top chunks to retrieve for answer",
        min_value=1,
        max_value=10,
        value=5,
        key=widget_key("answer_top_k")
    )

    if st.button("Generate Answer from Research DB"):

        if not answer_question.strip():
            st.warning("Please enter a question.")
            st.stop()

        with st.spinner("Retrieving relevant chunks..."):

            retrieved_chunks = retrieve_relevant_chunks(
                vector_store=st.session_state["vector_store"],
                question=answer_question,
                k=answer_top_k
            )

        st.session_state["retrieved_chunks"] = retrieved_chunks

        st.subheader("Retrieved Chunks Used for Answer")

        for item in retrieved_chunks:

            st.markdown(f"### Rank {item['rank']}")
            st.write(f"Similarity Score: {item['score']}")
            st.write(f"Title: {item['title']}")
            st.write(f"URL: {item['url']}")

            if "source_type" in item:
                st.write(f"Source Type: {item['source_type']}")

            if "source_id" in item:
                st.write(f"Source ID: {item['source_id']}")

            st.text_area(
                "Retrieved Chunk",
                item["content"][:2000],
                height=250,
                key=f"answer_retrieved_{item['rank']}"
            )

            st.divider()

        with st.spinner("Generating final answer using Gemini..."):

            final_answer = generate_answer_from_chunks(
                question=answer_question,
                retrieved_chunks=retrieved_chunks
            )

        st.subheader("Final Answer")
        st.write(final_answer)


# =========================
# RESET SECTION
# =========================

st.divider()

if st.button("Clear Recent Data", key=widget_key("clear_recent_data_btn")):
    reset_loaded_data()
    st.success("All recent data cleared. App reset to initial state.")
    st.rerun()