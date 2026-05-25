from google import genai

from src.config import GEMINI_API_KEY


MODEL_NAME = "models/gemini-2.5-flash-lite"


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