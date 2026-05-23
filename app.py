import asyncio
import streamlit as st

from src.config import SERPER_API_KEY
from src.serper_search import search_serper
from src.web_extractor import extract_content
from src.document_processor import process_extracted_content


st.set_page_config(
    page_title="Easy Answer - Module Test",
    page_icon="🧪",
    layout="wide"
)

st.title("🧪 Easy Answer - Module Testing App")

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