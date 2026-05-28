# src/session_state.py

import streamlit as st


def initialize_session_state():
    """
    Initialize all required Streamlit session state variables.
    Call this once near the top of app_1.2.py after st.set_page_config().
    """

    defaults = {
        "reset_counter": 0,
        "db_mode_selected": False,
        "active_db_name": None,
        "active_topic_folder": None,
        "qa_history": [],
        "all_chunks": [],
        "successful_documents": [],
    }

    for key, default_value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default_value


def widget_key(name: str) -> str:
    """
    Creates dynamic widget keys.
    Used to reset Streamlit widgets after clearing input/session.
    """
    return f"{name}_{st.session_state['reset_counter']}"


def reset_loaded_data():
    """
    Clears the currently loaded database/session data.
    Also clears related Streamlit widgets.
    """

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
        if key in keys_to_clear or any(
            key.startswith(prefix) for prefix in widget_prefixes_to_clear
        ):
            del st.session_state[key]

    st.session_state["reset_counter"] = st.session_state.get("reset_counter", 0) + 1


def reset_input_fields_only():
    """
    Clears only source input widgets after successful data loading.
    Keeps active database and Q/A history untouched.
    """

    widget_prefixes_to_clear = [
        "source_input",
        "google_num_results",
        "file_uploader",
    ]

    for key in list(st.session_state.keys()):
        if any(key.startswith(prefix) for prefix in widget_prefixes_to_clear):
            del st.session_state[key]

    st.session_state["reset_counter"] = st.session_state.get("reset_counter", 0) + 1