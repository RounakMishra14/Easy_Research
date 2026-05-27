import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="Easy Answer UI Test",
    page_icon="🧠",
    layout="wide"
)

# =========================
# SESSION STATE
# =========================

if "qa_history" not in st.session_state:
    st.session_state["qa_history"] = []

if "active_db" not in st.session_state:
    st.session_state["active_db"] = "combined_research_db | 27.05.2026 - 06:36 PM"


# =========================
# SIDEBAR
# =========================

st.sidebar.header("Research History")

st.sidebar.success("Active Database")
st.sidebar.write(st.session_state["active_db"])

history_items = [
    "combined_research_db | 27.05.2026 - 06:36 PM",
    "AI Agents | 27.05.2026 - 06:29 PM",
    "RAG Notes | 27.05.2026 - 06:27 PM",
]

selected_db = st.sidebar.selectbox(
    "History",
    history_items
)

if st.sidebar.button("Switch Database"):
    st.session_state["active_db"] = selected_db
    st.rerun()

st.sidebar.divider()

if st.sidebar.button("Clear Current Session"):
    st.session_state["qa_history"] = []
    st.success("Session cleared.")
    st.rerun()


# =========================
# CUSTOM CSS
# =========================

st.markdown("""
<style>
.main-title {
    font-size: 42px;
    font-weight: 800;
    margin-bottom: 6px;
}

.subtitle {
    color: #aaa;
    font-size: 16px;
    margin-bottom: 30px;
}

.db-pill {
    display: inline-block;
    padding: 8px 14px;
    border-radius: 999px;
    background: #1f6f43;
    color: white;
    font-size: 14px;
    margin-bottom: 25px;
}

.chat-card {
    border: 1px solid #333;
    border-radius: 18px;
    padding: 18px;
    margin-bottom: 16px;
    background-color: #1f1f28;
}

.question {
    font-weight: 700;
    font-size: 17px;
    margin-bottom: 8px;
}

.answer {
    color: #ddd;
    font-size: 15px;
    line-height: 1.6;
}

.time {
    color: #888;
    font-size: 12px;
    margin-top: 8px;
}

.composer {
    border: 1px solid #333;
    border-radius: 20px;
    padding: 18px;
    background-color: #1f1f28;
    margin-top: 20px;
}
</style>
""", unsafe_allow_html=True)


# =========================
# HEADER
# =========================

st.markdown('<div class="main-title">🧠 Easy Answer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Search Google, paste URLs, add PDFs/TXT files, and ask questions from your research database.</div>',
    unsafe_allow_html=True
)

st.markdown(
    f'<div class="db-pill">Active DB: {st.session_state["active_db"]}</div>',
    unsafe_allow_html=True
)


# =========================
# DATA EXTRACT COMPOSER
# =========================

st.markdown("### Add Data")

with st.container(border=True):

    source_input = st.text_area(
        "Search topic or paste URLs",
        placeholder=(
            "Example:\n"
            "latest AI agents in healthcare\n\n"
            "https://example.com/article\n"
            "https://youtube.com/watch?v=xxxx"
        ),
        height=180
    )

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        uploaded_files = st.file_uploader(
            "➕ Add TXT / PDF",
            type=["txt", "pdf"],
            accept_multiple_files=True
        )

    with col2:
        web_pages = st.number_input(
            "Web pages",
            min_value=1,
            max_value=50,
            value=5,
            step=1
        )

    with col3:
        st.write("")
        st.write("")
        load_clicked = st.button("Load Data", use_container_width=True)

if load_clicked:
    lines = [line.strip() for line in source_input.splitlines() if line.strip()]

    urls = [line for line in lines if line.startswith("http")]
    search_queries = [line for line in lines if not line.startswith("http")]

    st.success("UI test only: Data loading simulation completed.")

    if search_queries:
        st.info(f"Google search query detected: {' '.join(search_queries)}")

    if urls:
        st.info(f"URLs detected: {len(urls)}")

    if uploaded_files:
        st.info(f"Files detected: {len(uploaded_files)}")


# =========================
# QUESTION / ANSWER HISTORY
# =========================

st.divider()
st.markdown("### Conversation History")

if st.session_state["qa_history"]:
    for item in st.session_state["qa_history"]:
        st.markdown(
            f"""
            <div class="chat-card">
                <div class="question">Q: {item["question"]}</div>
                <div class="answer">{item["answer"]}</div>
                <div class="time">{item["time"]}</div>
            </div>
            """,
            unsafe_allow_html=True
        )
else:
    st.caption("No questions asked yet.")


# =========================
# ASK QUESTION COMPOSER
# =========================

st.markdown("### Ask from Research Database")

with st.container(border=True):

    question = st.text_input(
        "Ask a question",
        placeholder="Ask anything from your loaded research database..."
    )

    col_a, col_b = st.columns([1, 1])

    with col_a:
        chunks = st.number_input(
            "Chunks to consider",
            min_value=1,
            max_value=50,
            value=5,
            step=1
        )

    with col_b:
        st.write("")
        st.write("")
        ask_clicked = st.button("Generate Answer", use_container_width=True)

if ask_clicked:
    if not question.strip():
        st.warning("Please enter a question.")
    else:
        fake_answer = (
            f"This is a UI test answer for: '{question}'. "
            f"In the real app, this will come from your FAISS vector database using top {chunks} chunks."
        )

        st.session_state["qa_history"].append(
            {
                "question": question,
                "answer": fake_answer,
                "time": datetime.now().strftime("%d.%m.%Y - %I:%M %p")
            }
        )

        st.rerun()