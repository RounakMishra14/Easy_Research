# 🧠 Easy Answer — Multi-Source RAG Research Assistant

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge\&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-App-red?style=for-the-badge\&logo=streamlit)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-green?style=for-the-badge)
![RAG](https://img.shields.io/badge/Architecture-RAG-purple?style=for-the-badge)
![LLM](https://img.shields.io/badge/LLM-Gemini%20%7C%20Groq%20%7C%20Ollama-orange?style=for-the-badge)

---

## 📌 Project Overview

**Easy Answer** is a modular **Retrieval-Augmented Generation (RAG)** application built with **Streamlit**.
It allows users to collect information from multiple sources, convert that information into embeddings, store it in a local vector database, and ask grounded questions based on the saved knowledge base.

The app supports multiple input sources such as:

* 🔍 Google/Serper search queries
* 🌐 Website URLs
* ▶️ YouTube video transcripts
* 📄 PDF files
* 📝 Text/document ingestion
* 🧠 Local and API-based LLMs

The main goal of this project is to create a reusable research assistant that can collect data, store it as a searchable vector database, and generate citation-based answers.

---

## ✨ Key Features

### 🔎 Multi-Source Data Collection

Users can provide:

* Search queries
* Single or multiple URLs
* YouTube links
* PDF files
* Text-based files

The system extracts content from these sources and converts it into clean document chunks.

---

### 🧩 Modular Code Structure

The project is separated into multiple reusable modules inside the `src/` folder.

This makes the app easier to debug, extend, and maintain.

---

### 🧠 RAG-Based Answer Generation

The application follows a RAG pipeline:

```text
User Input
   ↓
Data Extraction
   ↓
Text Processing
   ↓
Chunking
   ↓
Embedding Generation
   ↓
FAISS Vector Store
   ↓
Relevant Chunk Retrieval
   ↓
LLM-Based Final Answer
```

---

### 💾 Local Vector Database

The app stores research databases locally inside:

```text
vector_store/
```

Each database has its own folder containing:

* FAISS index
* Metadata
* Source details
* Chunk information

---

### 🗂️ Research History Management

The app keeps track of previously created research databases.

Users can:

* View saved databases
* Load existing databases
* Continue asking questions from saved data
* Delete old databases safely

---

### 🤖 Multiple LLM Provider Support

The answer generation module supports:

* Google Gemini
* Groq
* Ollama local models

This allows switching between cloud-based and local LLM workflows.

---

## 🏗️ Project Structure

```text
Easy_Answer/
│
├── app_1.1.py
├── app.py
├── requirements.txt
├── .env
├── .gitignore
│
├── src/
│   ├── answer_generator.py
│   ├── config.py
│   ├── document_processor.py
│   ├── file_ingestor.py
│   ├── history_manager.py
│   ├── input_parser.py
│   ├── pdf_loader.py
│   ├── retriever.py
│   ├── serper_search.py
│   ├── session_state.py
│   ├── vector_store.py
│   ├── web_extractor.py
│   ├── youtube_loader.py
│   └── __init__.py
│
├── notebooks/
│   └── 01_serper_test.ipynb
│
└── notes/
```

---

## 🧠 Technical Workflow

### 1. User Input Handling

The app accepts different input types from the Streamlit UI.

Main file:

```text
app_1.1.py
```

Input parsing logic is handled in:

```text
src/input_parser.py
```

This module helps detect whether the user input is:

* A normal search query
* A regular URL
* A YouTube URL
* A mixed input containing both URLs and search text

---

### 2. Web Search Using Serper API

Search-based input is processed through:

```text
src/serper_search.py
```

This module sends the user query to the Serper API and retrieves search results.

---

### 3. Website Content Extraction

URL-based content extraction is handled in:

```text
src/web_extractor.py
```

This module extracts readable text content from web pages.

---

### 4. YouTube Transcript Extraction

YouTube links are processed through:

```text
src/youtube_loader.py
```

This extracts transcript text from YouTube videos where transcripts are available.

---

### 5. PDF Processing

PDF files are processed using:

```text
src/pdf_loader.py
```

The module extracts text content from uploaded PDF documents.

---

### 6. Document Chunking

Extracted content is converted into chunks using:

```text
src/document_processor.py
```

Chunking is important because LLMs and vector databases work better with smaller text segments instead of large documents.

---

### 7. Vector Store Creation

Embeddings and FAISS vector database creation are handled in:

```text
src/vector_store.py
```

The app creates a searchable local vector database from processed document chunks.

---

### 8. Relevant Chunk Retrieval

When the user asks a question, the app searches the vector database using:

```text
src/retriever.py
```

This retrieves the most relevant chunks for the user’s question.

---

### 9. Final Answer Generation

The final RAG prompt and LLM response are handled in:

```text
src/answer_generator.py
```

This file contains logic for:

* Building citation-based RAG context
* Creating the final prompt
* Calling Gemini
* Calling Groq
* Calling Ollama
* Returning the final grounded answer

---

## 🧾 RAG Prompt Design

The app builds a structured prompt containing:

* User question
* Retrieved context
* Citation numbers
* Source URLs
* Strict grounding rules

Example answer format:

```text
## Answer

Generated answer with citations like [1], [2].

## Sources

[1] Source title - URL
[2] Source title - URL
```

This helps reduce hallucination and improves traceability.

---

## 🗃️ Database History System

Database history is managed through:

```text
src/history_manager.py
```

This module handles:

* Creating topic-based database folders
* Saving metadata
* Loading database history
* Sorting databases by creation time
* Deleting selected research databases

Each research database is saved with a unique folder name based on topic and timestamp.

---

## 🧼 Session State Management

Streamlit session variables are managed in:

```text
src/session_state.py
```

This keeps UI state cleaner and avoids putting too much session logic directly inside the main app file.

It handles:

* Default session values
* Widget keys
* Resetting loaded data
* Resetting input fields

---

## 🤖 LLM Provider Details

### Gemini

Requires:

```env
GEMINI_API_KEY=your_gemini_api_key
```

Default model example:

```text
gemini-2.5-flash-lite
```

---

### Groq

Requires:

```env
GROQ_API_KEY=your_groq_api_key
```

Default model example:

```text
llama-3.1-8b-instant
```

---

### Ollama

Ollama allows local model execution.

Example setup:

```bash
ollama pull phi3
ollama run phi3
```

The app calls Ollama through:

```text
http://localhost:11434/api/generate
```

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/Easy_Answer.git
cd Easy_Answer
```

---

### 2. Create virtual environment

```bash
python -m venv venv
```

Activate it on Windows:

```bash
venv\Scripts\activate
```

Activate it on macOS/Linux:

```bash
source venv/bin/activate
```

---

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

### 4. Create `.env` file

Create a `.env` file in the root directory:

```env
SERPER_API_KEY=your_serper_api_key
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
LLM_PROVIDER=gemini
OLLAMA_MODEL=phi3
```

Do not push `.env` to GitHub.

---

## ▶️ Run the App

Run the Streamlit app:

```bash
streamlit run app_1.1.py
```

---

## 🧪 Example Usage

### Search-based research

```text
What is retrieval augmented generation?
```

The app will search the web, extract relevant content, create a vector database, and answer based on retrieved chunks.

---

### URL-based research

```text
https://example.com/article
```

The app will extract content from the URL and store it in the vector database.

---

### Mixed input

```text
Explain RAG architecture using this URL https://example.com/rag-guide
```

The app can separate query text and URLs, process both, and create one combined database.

---

### Ask from saved database

After loading an existing vector database, users can ask:

```text
Summarize the main findings.
```

or

```text
Give the answer with sources.
```

---

## 🛡️ Security Notes

Do not commit sensitive files such as:

```text
.env
API keys
local vector databases
large PDF files
temporary cache files
```

Recommended `.gitignore` entries:

```gitignore
.env
venv/
__pycache__/
*.pyc
vector_store/
.streamlit/secrets.toml
```

---

## 🚀 Future Improvements

Planned or possible improvements:

* Add chat memory for last generated answers
* Add support for DOCX and CSV files
* Add export answer as PDF
* Add better UI with modern chat layout
* Add source filtering
* Add model selection from sidebar
* Add token usage tracking
* Add database rename option
* Add user authentication
* Add deployment support

---

## 🧰 Tech Stack

| Area                   | Technology                          |
| ---------------------- | ----------------------------------- |
| Frontend               | Streamlit                           |
| Language               | Python                              |
| Search API             | Serper                              |
| Web Extraction         | BeautifulSoup / Trafilatura         |
| PDF Processing         | PyMuPDF                             |
| YouTube Transcript     | youtube-transcript-api              |
| Embeddings             | Sentence Transformers / HuggingFace |
| Vector Store           | FAISS                               |
| LLM Providers          | Gemini, Groq, Ollama                |
| Environment Management | python-dotenv                       |

---

## 📌 Current Main App File

The latest modular version is:

```text
app_1.1.py
```

Older or testing versions may exist in the repository, such as:

```text
app.py
app_1.0.py
app_1.2.py
app_test_UI.py
```

For production or demonstration, use the latest stable app file.

---

## 🧠 Why This Project Matters

This project demonstrates practical implementation of a modern AI research assistant using:

* Modular Python architecture
* Multi-source data ingestion
* Local vector database storage
* RAG-based answer generation
* Citation-supported responses
* Multiple LLM backend support
* Streamlit-based interactive UI

It is useful for learning and demonstrating how real-world AI applications combine search, extraction, embeddings, retrieval, and LLM reasoning into one complete workflow.

---

## 👨‍💻 Author

Built as a modular AI research assistant project for experimenting with RAG, vector databases, and LLM-powered question answering.

---
