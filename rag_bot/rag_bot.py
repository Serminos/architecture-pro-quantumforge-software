import sys
import time
from pathlib import Path
from typing import List, Tuple


# Добавляем путь к проекту
sys.path.append(str(Path(__file__).parent.parent))

from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document

from config import (
    INDEX_DIR, EMBEDDING_MODEL, LLM_TYPE,
    OLLAMA_MODEL, HF_MODEL, OPENAI_MODEL,
    OPENAI_API_KEY, TOP_K
)


# ========== 1. Загрузка индекса ==========
def load_index():
    """Загружает векторный индекс FAISS и модель эмбеддингов."""
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


# ========== 2. Поиск релевантных чанков ==========
def retrieve(vectorstore, query: str, k: int = TOP_K) -> List[Document]:
    """Возвращает k наиболее релевантных чанков."""
    docs = vectorstore.similarity_search(query, k=k)
    return docs


# ========== 3. Формирование промпта с Few-shot и CoT ==========
def build_prompt(query: str, retrieved_docs: List[Document]) -> str:
    """
    Строит промпт для LLM с:
    - системной инструкцией (Chain-of-Thought)
    - контекстом из найденных чанков
    - Few-shot примерами (2 примера)
    - пользовательским запросом
    """
    # Системная инструкция с CoT
    system = (
        "Ты - помощник, специализирующийся на вселенной «Хроники Междумирья».\n"
        "В твоей базе знаний содержатся данные о персонажах, планетах, технологиях, организациях и событиях.\n"
        "ОТВЕЧАЙ ТОЛЬКО НА РУССКОМ ЯЗЫКЕ. НЕ ИСПОЛЬЗУЙ КИТАЙСКИЙ, АНГЛИЙСКИЙ ИЛИ ДРУГИЕ ЯЗЫКИ.\n"
        "Перед ответом обязательно выполни следующие шаги (Chain-of-Thought):\n"
        "1. Перечисли ключевые сущности из запроса.\n"
        "2. Найди в предоставленных документах информацию, связанную с этими сущностями.\n"
        "3. Сформулируй ответ на основе найденных фактов.\n"
        "4. Если информация отсутствует, честно скажи: «Я не знаю».\n\n"
        "Твой ответ должен быть на русском языке, кратким и по делу.\n"
    )

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
    prompt = (
        f"{system}\n\n"
        f"=== ДОКУМЕНТЫ ИЗ БАЗЫ ЗНАНИЙ ===\n{context}\n\n"
        f"=== ПРИМЕРЫ ОТВЕТОВ ===\n{few_shot_examples}\n"
        f"=== ТЕКУЩИЙ ЗАПРОС ===\n"
        f"Вопрос: {query}\n"
        f"Ответ (с размышлениями):\n"
    )
    return prompt


# ========== 4. Генерация ответа через LLM ==========
def generate_answer(prompt: str) -> str:
    """Отправляет промпт в выбранную LLM и возвращает ответ."""

    if LLM_TYPE == "ollama":
        import requests
        #print(prompt)
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
def main():
    print("=" * 60)
    print("🤖 RAG-бот для вселенной «Хроники Междумирья»")
    print("   (с Few-shot и Chain-of-Thought)")
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

        # Поиск
        docs = retrieve(vectorstore, query)
        if not docs:
            print("⚠️ Ничего не найдено. Попробуйте другой вопрос.")
            continue

        # Формируем промпт
        prompt = build_prompt(query, docs)

        # Генерируем ответ
        print("⏳ Думаю...")
        start = time.time()
        answer = generate_answer(prompt)
        elapsed = time.time() - start

        # Вывод результата
        print("\n" + "=" * 60)
        print(f"💬 Ответ (за {elapsed:.1f} сек):")
        print(answer)
        print("=" * 60)


if __name__ == "__main__":
    main()
