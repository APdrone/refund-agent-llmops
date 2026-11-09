import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

load_dotenv()

# Configurable model with sensible defaults
MODEL_NAME = os.getenv("LLM_MODEL", "gpt-6-luna")
MODEL_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.0"))

model = init_chat_model(
    model=MODEL_NAME,
    model_provider=MODEL_PROVIDER,
    temperature=TEMPERATURE
)
