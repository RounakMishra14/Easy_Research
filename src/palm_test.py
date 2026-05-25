from google import genai
from src.config import GEMINI_API_KEY


def list_available_models():
    client = genai.Client(api_key=GEMINI_API_KEY)
    model_names = []

    for model in client.models.list():
        model_names.append(model)
    return model_names

def test_gemini():
    client = genai.Client(api_key=GEMINI_API_KEY)
    

    response = client.models.generate_content(
        model= "gemini-2.5-flash-lite",
        contents = "Explain RAG in 3 simple lines."
    )

    return response.text