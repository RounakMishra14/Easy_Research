import streamlit as st

from src.palm_test import list_available_models, test_gemini

st.title("Gemini API Test")


if st.button("List Available models"):
    models=list_available_models()
    st.write(models)
    
if st.button("Test Gemini"):
    try:
        result = test_gemini()

        st.success("Gemini Test successful.")
        st.write(result)

    except Exception as e:
        st.error("Gemini test failed.")
        st.exception(e)