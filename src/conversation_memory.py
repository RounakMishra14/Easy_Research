# src/conversation_memory.py

import streamlit as st


MAX_MEMORY_ITEMS = 2


def save_generated_answer(question: str, answer: str):
    """
    Save latest generated answer into session memory.
    Keeps only last N answers.
    """

    if "recent_answers" not in st.session_state:
        st.session_state["recent_answers"] = []

    st.session_state["recent_answers"].append({
        "question": question,
        "answer": answer
    })

    # Keep only last N answers
    st.session_state["recent_answers"] = (
        st.session_state["recent_answers"][-MAX_MEMORY_ITEMS:]
    )


def get_recent_answers():
    """
    Return raw recent answers list.
    """

    return st.session_state.get("recent_answers", [])


def get_recent_answers_context() -> str:
    """
    Convert previous answers into prompt context.
    """

    recent_answers = get_recent_answers()

    if not recent_answers:
        return ""

    context_parts = []

    for idx, item in enumerate(recent_answers, start=1):

        formatted_memory = f"""
Previous Conversation {idx}

Previous User Question:
{item.get("question", "")}

Previous Assistant Answer:
{item.get("answer", "")}
"""

        context_parts.append(formatted_memory)

    final_context = "\n".join(context_parts)

    return final_context


def clear_recent_answers():
    """
    Clear memory buffer.
    """

    st.session_state["recent_answers"] = []