'''
from google import genai
from src.config import GEMINI_API_KEY
MODEL_NAME = "models/gemini-2.5-flash-lite" 
MODEL_NAME = "models/gemini-3.5-flash"



def get_gemini_client():
    """
    Create Gemini client.
    """

    if not GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY not found in .env file."
        )

    client = genai.Client(
        api_key=GEMINI_API_KEY
    )

    return client


def build_context_from_chunks(retrieved_chunks):
    """
    Build RAG context from retrieved chunks.
    """

    context_parts = []

    for item in retrieved_chunks:

        source_text = f"""
Source Rank: {item["rank"]}

Title:
{item.get("title", "")}

URL:
{item.get("url", "")}

Content:
{item.get("content", "")}
"""

        context_parts.append(source_text)

    return "\n\n".join(context_parts)


def generate_answer_from_chunks(
    question,
    retrieved_chunks
):
    """
    Generate grounded answer from retrieved chunks.
    """

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not retrieved_chunks:
        raise ValueError("No retrieved chunks found.")

    client = get_gemini_client()

    context = build_context_from_chunks(
        retrieved_chunks
    )

    prompt = f"""
You are an advanced AI research assistant.

Answer the user question ONLY from the provided retrieved context.

Rules:
1. Do not hallucinate.
2. Do not invent facts.
3. If information is insufficient, clearly say so.
4. Keep answers structured and readable.
5. Mention important source URLs used.
6. Prefer factual grounded answers.

User Question:
{question}

Retrieved Context:
{context}

Final Answer:
"""

    response = client.models.generate_content(
        model=MODEL_NAME,
        contents=prompt
    )
    return response.text

'''

import os
import requests
from dotenv import load_dotenv
from src.conversation_memory import get_recent_answers_context
load_dotenv()


def build_context_from_chunks(retrieved_chunks):
    """
    Build RAG context from retrieved chunks.
    """

    context_parts = []

    for i, item in enumerate(retrieved_chunks, start=1):

        source_text = f"""
Citation Number: [{i}]

Title:
{item.get("title", "")}

URL:
{item.get("url", "")}

Content:
{item.get("content", "")}
"""
        context_parts.append(source_text)

    return "\n\n".join(context_parts)


def build_rag_prompt(question, retrieved_chunks):
    """
    Build final RAG prompt.
    """

    context = build_context_from_chunks(retrieved_chunks)
    recent_context = get_recent_answers_context()
    prompt = f"""
You are an advanced AI research assistant.

Answer the user question ONLY from the provided retrieved context.

Rules:
1. Answer ONLY from the retrieved context.
2. Do not hallucinate or invent facts.
3. Use citation numbers inside the answer like [1], [2], [3].
4. Do NOT paste full URLs inside the main answer.
5. At the end, add a section named "Sources".
6. In Sources, list only the citation number, title, and URL.
7. If multiple chunks have the same URL, mention it only once.
8. Keep the answer clean, structured, and readable.

Required answer format:

## Answer

Write the answer here using citations like [1], [2].

## Sources

[1] Title - URL
[2] Title - URL

Conversation Memory:
{recent_context}

User Question:
{question}


Retrieved Context:
{context}


Final Answer:
"""

    return prompt


def generate_with_gemini(prompt, model_name=None):
    """
    Generate answer using Gemini.
    """

    from google import genai

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file.")

    model_name = model_name or os.getenv(
        "GEMINI_MODEL",
        "gemini-2.5-flash-lite"
        #"gemini-3.5-flash"
    )

    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model=model_name,
        contents=prompt
    )

    return response.text


def generate_with_groq(prompt, model_name=None):
    """
    Generate answer using Groq.
    """

    from groq import Groq

    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in .env file.")

    model_name = model_name or os.getenv(
        "GROQ_MODEL",
        "llama-3.1-8b-instant"
    )

    client = Groq(api_key=api_key)

    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {
                "role": "system",
                "content": "You are a grounded research assistant."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        temperature=0.2
    )

    return response.choices[0].message.content


def generate_with_ollama(prompt, model_name=None):
    """
    Generate answer using local Ollama.
    """

    model_name = model_name or os.getenv(
        "OLLAMA_MODEL",
        "phi3"
    )

    response = requests.post(
        "http://localhost:11434/api/generate",
        json={
            "model": model_name,
            "prompt": prompt,
            "stream": False
        },
        timeout=300
    )

    response.raise_for_status()

    return response.json()["response"]


def generate_answer_from_chunks(
    question,
    retrieved_chunks,
    provider=None,
    model_name=None
):
    """
    Main function used by app.py.

    provider options:
    - gemini
    - groq
    - ollama
    """

    if not question.strip():
        raise ValueError("Question cannot be empty.")

    if not retrieved_chunks:
        raise ValueError("No retrieved chunks found.")

    provider = provider or os.getenv("LLM_PROVIDER", "gemini")
    provider = provider.lower().strip()

    prompt = build_rag_prompt(
        question=question,
        retrieved_chunks=retrieved_chunks
    )

    if provider == "gemini":
        return generate_with_gemini(
            prompt=prompt,
            model_name=model_name
        )

    if provider == "groq":
        return generate_with_groq(
            prompt=prompt,
            model_name=model_name
        )

    if provider == "ollama":
        return generate_with_ollama(
            prompt=prompt,
            model_name=model_name
        )

    raise ValueError(
        f"Unsupported provider '{provider}'. Use gemini, groq, or ollama."
    )