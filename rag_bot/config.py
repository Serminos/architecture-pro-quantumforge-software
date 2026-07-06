import os
from pathlib import Path

# Пути
BASE_DIR = Path(__file__).parent.parent
INDEX_DIR = BASE_DIR / "vector_index" / "indices" / "faiss_index"
DOCS_DIR = BASE_DIR / "knowledge_base" / "final"

# Модель эмбеддингов (та же, что и при индексации)
EMBEDDING_MODEL = "BAAI/bge-m3"

# LLM — выберите один из вариантов:
# 1) локальная через Ollama (установите ollama и модель)
# 2) локальная через HuggingFace (transformers)
# 3) OpenAI (требуется API ключ)

LLM_TYPE = "ollama"          # "ollama" | "huggingface" | "openai"
#LLM_TYPE = "huggingface"          # "ollama" | "huggingface" | "openai"
OLLAMA_MODEL = "qwen2.5:7b"  # модель в Ollama
HF_MODEL = "Qwen/Qwen2.5-7B-Instruct"  # для huggingface
#HF_MODEL = "yandex/YandexGPT-5-Lite-8B-instruct"  # для huggingface
OPENAI_MODEL = "gpt-4o-mini"            # для OpenAI

# OpenAI ключ (если используется)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")

# Параметры поиска
TOP_K = 5

# Уровень защиты по умолчанию (0 – без защиты)
SECURITY_LEVEL = 3