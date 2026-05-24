import asyncio
import streamlit as st

from src.config import SERPER_API_KEY
from src.serper_search import search_serper
from src.web_extractor import extract_content
from src.document_processor import process_extracted_content
#from src.token_utils import get_chunk_token_report #(Token Size ~ Chunk size comparation)
#from src.embedding_debugger import get_embedding_debug_dataframe #(for embedding debugging)
from src.embedding_debugger import save_embedding_debug_csv #(for embedding debugging)
from src.vector_store import get_embedding_model #(for embedding debugging)

from datetime import datetime

from src.history_manager import (
    create_topic_folder,
    save_metadata,
    list_research_history
)

from src.vector_store import (
    create_and_save_vector_store,
    load_vector_store
)


st.set_page_config(
    page_title="Easy Answer - Module Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Easy Answer - Module Testing App")

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

st.write(
    "This app tests Serper search, webpage extraction, "
    "LangChain document creation, and chunking."
)

if SERPER_API_KEY:
    st.success("SERPER_API_KEY loaded successfully.")
else:
    st.error("SERPER_API_KEY not found. Check your .env file.")

query = st.text_input("Enter search query", value="latest AI agents")

num_results = st.slider(
    "Number of URLs to test",
    min_value=1,
    max_value=10,
    value=3
)

if st.button("Run Module Test"):
    if not SERPER_API_KEY:
        st.stop()

    all_chunks = []
    successful_documents = []

    with st.spinner("Step 1: Searching with Serper..."):
        results = search_serper(query, num_results)

    st.subheader("Step 1 Result: Serper Search")
    st.write(f"Results returned after filtering: {len(results)}")

    for idx, result in enumerate(results, start=1):
        st.markdown(f"### {idx}. {result['title']}")
        st.write(result["link"])
        st.write(result["snippet"])

    st.divider()

    st.subheader("Step 2 + 3: Extract Content and Create Chunks")

    for idx, result in enumerate(results, start=1):
        st.markdown(f"## URL {idx}: {result['title']}")
        st.write(result["link"])

        with st.spinner(f"Extracting URL {idx}..."):
            extracted_item = asyncio.run(
                extract_content(
                    url=result["link"],
                    title=result["title"],
                    snippet=result["snippet"]
                )
            )

        if extracted_item["content"]:
            st.success(
                f"Extraction successful using: "
                f"{extracted_item['extraction_method']}"
            )

            st.text_area(
                "Extracted Content Preview",
                extracted_item["content"][:3000],
                height=300,
                key=f"content_{idx}"
            )

            chunks = process_extracted_content(extracted_item)

            st.success(f"Chunking successful. Total chunks created: {len(chunks)}")

            all_chunks.extend(chunks)
            successful_documents.append(extracted_item)

            #Chunk Size ~ Token size comparation:-
            '''token_report_df = get_chunk_token_report(chunks)

            st.subheader("Chunk Token Report")
            st.dataframe(token_report_df)

            st.write("Token Summary")
            st.json({
                "total_chunks": len(chunks),
                "min_tokens": int(token_report_df["token_count"].min()),
                "max_tokens": int(token_report_df["token_count"].max()),
                "avg_tokens": round(float(token_report_df["token_count"].mean()), 2),
                "chunks_above_512": int((token_report_df["token_count"] > 512).sum())
            })'''

            if chunks:
                st.write("First chunk metadata:")
                st.json(chunks[0].metadata)

                st.text_area(
                    "First Chunk Preview",
                    chunks[0].page_content[:1500],
                    height=250,
                    key=f"chunk_{idx}"
                )

        else:
            st.error("Content extraction failed for this URL.")

        st.divider()

    st.session_state["all_chunks"] = all_chunks
    st.session_state["successful_documents"] = successful_documents
    st.session_state["query"] = query

    st.success(
        f"Processing completed. Total chunks collected from all URLs: {len(all_chunks)}"
    )


if "all_chunks" in st.session_state and st.session_state["all_chunks"]:

    if st.button("Create and Save Embeddings"):
        with st.spinner("Creating embeddings and saving FAISS vector store..."):

            topic_folder = create_topic_folder(st.session_state["query"])

            
            # ==========================================
            # EMBEDDING DEBUGGING SECTION
            # ==========================================

            embedding_model = get_embedding_model()

            embedding_debug_csv_path, embedding_debug_df = save_embedding_debug_csv(
                chunks=st.session_state["all_chunks"],
                embeddings_model=embedding_model,
                save_folder=topic_folder
            )
            
            st.subheader("Embedding Debug Information")
            
            st.dataframe(
                embedding_debug_df.head(),
                use_container_width=True
            )
            
            st.success("Full embedding debug CSV saved successfully.")
            st.code(embedding_debug_csv_path)
            
            

            vector_store = create_and_save_vector_store(
                chunks=st.session_state["all_chunks"],
                save_path=topic_folder
            )

            metadata = {
                "topic": st.session_state["query"],
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "total_chunks": len(st.session_state["all_chunks"]),
                "total_sources": len(st.session_state["successful_documents"]),
                "embedding_model": "BAAI/bge-base-en-v1.5",
                "vector_store_type": "FAISS",
                "storage_path": topic_folder
            }

            save_metadata(topic_folder, metadata)

            st.session_state["vector_store"] = vector_store

            st.success("Embeddings created and saved successfully.")
            st.code(topic_folder)
            st.rerun()