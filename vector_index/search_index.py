import os
from pathlib import Path
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Абсолютные пути
SCRIPT_DIR = Path(__file__).parent
INDEX_DIR = SCRIPT_DIR / "indices" / "faiss_index"
MODEL_NAME = "BAAI/bge-m3"


def load_index():
    """Загружает индекс и модель (один раз!)."""
    print("Загрузка модели BGE-M3 на CPU...")

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 16
        }
    )

    print(f"Загрузка индекса из: {INDEX_DIR}")

    # Проверяем, что индекс существует
    index_file = INDEX_DIR / "index.faiss"
    if not index_file.exists():
        raise FileNotFoundError(
            f"Индекс не найден: {index_file}\n"
            f"   Запустите сначала build_index.py!"
        )

    vectorstore = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )

    print("Индекс загружен\n")
    return vectorstore


def search(query: str, vectorstore, k: int = 3):
    """Выполняет поиск."""
    results = vectorstore.similarity_search_with_score(query, k=k)
    return results


def print_results(query: str, results: list):
    """Красиво выводит результаты."""
    print(f"Запрос: '{query}'")
    print(f"Найдено: {len(results)} результатов")
    print("-" * 60)

    for i, (doc, score) in enumerate(results, 1):
        print(f"\n[{i}] Источник: {doc.metadata.get('filepath', 'unknown')}")
        print(f"    Категория: {doc.metadata.get('category', 'unknown')}")
        print(f"    Оценка: {score:.4f}")
        print(f"    Текст: {doc.page_content[:200]}...")
        print("-" * 40)

    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    # Загружаем индекс ОДИН раз
    try:
        vectorstore = load_index()
    except FileNotFoundError as e:
        print(e)
        exit(1)

    # Тестовые запросы
    queries = [
        "Кто такой Ivan Nebov?",
        "Что такое Svetomech?",
        "Где находится Sukhostep?",
        "Что такое Orden Vedunov?",
        "Что произошло в Bitva pri Zelyonoy Lune?"
    ]

    for query in queries:
        results = search(query, vectorstore, k=5)
        print_results(query, results)