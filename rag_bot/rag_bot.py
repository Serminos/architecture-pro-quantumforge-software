import sys
import time
import argparse
from pathlib import Path
from typing import List

sys.path.append(str(Path(__file__).parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config import (
    INDEX_DIR, EMBEDDING_MODEL, LLM_TYPE,
    OLLAMA_MODEL, HF_MODEL, OPENAI_MODEL,
    OPENAI_API_KEY, TOP_K, SECURITY_LEVEL
)

# Импортируем модуль безопасности
from security import (
    filter_malicious_chunks,
    get_system_prompt,
    filter_answer,
    sanitize_user_query,
    get_level_description,
)


# ========== 1. Загрузка индекса ==========
def load_index():
    print("🔄 Загрузка модели эмбеддингов...")
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 16}
    )
    print("📂 Загрузка индекса FAISS...")
    vectorstore = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )
    print("✅ Индекс загружен.")
    return vectorstore


# ========== 2. Поиск релевантных чанков (с фильтрацией) ==========
def retrieve(vectorstore, query: str, level: int, k: int = TOP_K) -> List[Document]:
    """Возвращает k наиболее релевантных чанков, применяя фильтрацию."""
    # Берём больше чанков для компенсации фильтрации
    docs = vectorstore.similarity_search(query, k=k * 2 if level >= 1 else k)
    # Фильтруем опасные
    docs = filter_malicious_chunks(docs, level)
    return docs[:k]


# ========== 3. Формирование промпта с CoT, Few-shot и динамическим pre-prompt ==========
def build_prompt(query: str, retrieved_docs: List[Document], level: int) -> str:
    """
    Строит промпт с системной инструкцией (в зависимости от уровня защиты),
    контекстом и Few-shot примерами.
    """
    # Системная инструкция из модуля безопасности (уровень >= 2)
    system = get_system_prompt(level)

    # Контекст из документов
    context = "\n\n".join([
        f"--- Источник: {doc.metadata.get('filepath', 'unknown')} ---\n{doc.page_content}"
        for doc in retrieved_docs
    ])

    # Few-shot примеры (2 примера из нашей базы)
    few_shot_examples = (
        "Вопрос: Кто такой Ivan Nebov?\n"
        "Размышления:\n"
        "1. Ключевые сущности: Ivan Nebov.\n"
        "2. В документах указано, что Ivan Nebov - легендарный мастер-ведун, сражавшийся в Velikaya Mezhdousobitsa.\n"
        "3. Формулирую ответ о его роли и происхождении.\n"
        "Ответ: Ivan Nebov - главный герой, мастер-ведун, родившийся на планете Sukhostep. Он сыграл ключевую роль в уничтожении Zvezda Smerti.\n\n"

        "Вопрос: Что такое Svetomech?\n"
        "Размышления:\n"
        "1. Ключевые сущности: Svetomech.\n"
        "2. В документах сказано, что это энергетическое оружие Ведунов, проецирующее клинок из плазмы.\n"
        "3. Формулирую определение.\n"
        "Ответ: Svetomech - это оружие Ведунов, представляющее собой клинок из плазмы. Используется для боя и является символом Ordena Vedunov.\n\n"
    )

    # Финальный промпт
    prompt_parts = []
    if system:
        prompt_parts.append(system)
    prompt_parts.append(f"=== ДОКУМЕНТЫ ИЗ БАЗЫ ЗНАНИЙ ===\n{context}")
    prompt_parts.append(f"=== ПРИМЕРЫ ОТВЕТОВ ===\n{few_shot_examples}")
    prompt_parts.append(f"=== ТЕКУЩИЙ ЗАПРОС ===\nВопрос: {query}\nОтвет (с размышлениями):")
    return "\n\n".join(prompt_parts)


# ========== 4. Генерация ответа через LLM ==========
def generate_answer(prompt: str) -> str:
    """Отправляет промпт в выбранную LLM и возвращает ответ."""

    if LLM_TYPE == "ollama":
        import requests
        # print(prompt)
        # Используем Ollama API
        url = "http://localhost:11434/api/generate"
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.3}
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            return response.json().get("response", "Ошибка генерации.")
        except Exception as e:
            return f"Ошибка при обращении к Ollama: {e}"
    elif LLM_TYPE == "huggingface":
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch

        print(f"🔄 Загрузка модели HuggingFace: {HF_MODEL} (это может занять время)...")

        # Загружаем токенизатор (без лишних параметров)
        tokenizer = AutoTokenizer.from_pretrained(
            HF_MODEL,
            trust_remote_code=True
        )

        # Загружаем модель (можно включить load_in_4bit=True, если нужно экономить VRAM)
        model = AutoModelForCausalLM.from_pretrained(
            HF_MODEL,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True)

        # Применяем шаблон чата (если модель его поддерживает)
        messages = [{"role": "user", "content": prompt}]
        try:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
        except Exception:
            # Если apply_chat_template не поддерживается, используем промпт как есть
            text = prompt

        inputs = tokenizer([text], return_tensors="pt").to(model.device)
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=500,
                temperature=0.3,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )

        response_ids = outputs[0][inputs["input_ids"].shape[1]:]
        response = tokenizer.decode(response_ids, skip_special_tokens=True)
        return response
    elif LLM_TYPE == "openai":
        from openai import OpenAI
        if not OPENAI_API_KEY:
            return "OPENAI_API_KEY не установлен."
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content

    else:
        return f"⚠️ Неизвестный тип LLM: {LLM_TYPE}"


# ========== 5. Основной цикл бота ==========
def main(level: int = SECURITY_LEVEL):
    print("=" * 60)
    print("🤖 RAG-бот для вселенной «Хроники Междумирья»")
    print("   (с Few-shot и Chain-of-Thought)")
    print(f"   Уровень защиты: {level} — {get_level_description(level)}")
    print("   Введите 'exit' для выхода.")
    print("=" * 60)

    # Загружаем индекс
    vectorstore = load_index()

    while True:
        query = input("\n❓ Задайте вопрос: ").strip()
        if query.lower() in ["exit", "quit", "q"]:
            print("До свидания!")
            break
        if not query:
            continue

        # 1. Проверка запроса на jailbreak (всегда активна)
        is_safe, reason = sanitize_user_query(query)
        if not is_safe:
            print(f"⛔ {reason}")
            print("⛔ Ответ: Я не могу обработать этот запрос.")
            continue

        # 2. Поиск с фильтрацией
        docs = retrieve(vectorstore, query, level)
        if not docs:
            print("⚠️ Ничего не найдено. Попробуйте другой вопрос.")
            continue

        # 3. Формируем промпт (с pre-prompt, если нужно)
        prompt = build_prompt(query, docs, level)

        # Генерируем ответ
        print("⏳ Думаю...")
        start = time.time()
        answer = generate_answer(prompt)
        elapsed = time.time() - start

        # 5. Пост-фильтрация ответа (уровень >= 3)
        answer = filter_answer(answer, level)

        # Вывод результата
        print("\n" + "=" * 60)
        print(f"💬 Ответ (за {elapsed:.1f} сек):")
        print(answer)
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--security-level",
        type=int,
        default=SECURITY_LEVEL,
        choices=[0, 1, 2, 3],
        help="Уровень защиты: 0-нет, 1-фильтр чанков, 2-+pre-prompt, 3-+пост-фильтр"
    )
    args = parser.parse_args()
    main(level=args.security_level)