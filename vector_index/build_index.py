import time
from pathlib import Path
from typing import List

# Установите HF_TOKEN для избежания warning
# os.environ["HF_TOKEN"] = "ваш_токен_тут"

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

# Абсолютные пути относительно скрипта
SCRIPT_DIR = Path(__file__).parent
DOCS_DIR = SCRIPT_DIR.parent / "knowledge_base" / "final"
INDEX_DIR = SCRIPT_DIR / "indices" / "faiss_index"

CHUNK_SIZE = 1536  # Увеличен для лучшего контекста
CHUNK_OVERLAP = 200
MODEL_NAME = "BAAI/bge-m3"


def load_documents(docs_dir: Path) -> List[Document]:
    """Загружает все текстовые файлы из папки."""
    documents = []

    if not docs_dir.exists():
        print(f"Папка не найдена: {docs_dir}")
        return documents

    file_paths = list(docs_dir.rglob("*.txt"))
    print(f"Найдено файлов: {len(file_paths)}")

    for file_path in file_paths:
        try:
            content = file_path.read_text(encoding="utf-8")
            if len(content.strip()) < 50:
                continue

            relative_path = file_path.relative_to(docs_dir)
            category = str(relative_path.parent) if relative_path.parent != Path(".") else "root"

            doc = Document(
                page_content=content,
                metadata={
                    "source": str(file_path),
                    "category": category,
                    "filename": file_path.stem,
                    "filepath": str(relative_path)
                }
            )
            documents.append(doc)
        except Exception as e:
            print(f"Ошибка {file_path}: {e}")

    return documents


def chunk_documents(documents: List[Document]) -> List[Document]:
    """Разбивает документы на чанки."""
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", ".", " ", ""]
    )

    chunked_docs = text_splitter.split_documents(documents)
    chunked_docs = [doc for doc in chunked_docs if len(doc.page_content.strip()) > 20]

    for i, doc in enumerate(chunked_docs):
        doc.metadata["chunk_id"] = i

    return chunked_docs


def build_index():
    print("=" * 60)
    print("ПОСТРОЕНИЕ ВЕКТОРНОГО ИНДЕКСА")
    print("=" * 60)

    # 1. Загрузка
    print("\nШаг 1: Загрузка документов...")
    documents = load_documents(DOCS_DIR)
    print(f"   Загружено: {len(documents)} документов")

    if not documents:
        print("Нет документов!")
        return

    # 2. Чанкинг
    print("\nШаг 2: Разбивка на чанки...")
    chunked_docs = chunk_documents(documents)
    print(f"   Создано: {len(chunked_docs)} чанков")

    # 3. Модель эмбеддингов
    print(f"\nШаг 3: Загрузка модели {MODEL_NAME}...")

    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={
            "normalize_embeddings": True,
            "batch_size": 16
        }
    )

    # 4. Создание индекса (CPU-only FAISS)
    print("\nШаг 4: Создание индекса FAISS...")
    start = time.time()

    vectorstore = FAISS.from_documents(
        documents=chunked_docs,
        embedding=embeddings
    )

    print(f"   Индекс создан за {time.time() - start:.2f} сек")

    # 5. Сохранение (создаем директорию если нужно)
    print("\nШаг 5: Сохранение...")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    # Удаляем старые файлы если есть
    for old_file in INDEX_DIR.glob("*"):
        old_file.unlink()

    vectorstore.save_local(str(INDEX_DIR))
    print(f"   Индекс сохранён в: {INDEX_DIR}")
    print(f"   Файлы: {list(INDEX_DIR.glob('*'))}")

    # 6. Статистика
    print("\n" + "=" * 60)
    print("СТАТИСТИКА")
    print("=" * 60)
    print(f"   Документов: {len(documents)}")
    print(f"   Чанков: {len(chunked_docs)}")
    print(f"   Chunk size: {CHUNK_SIZE}")
    print(f"   Устройство: CPU (Ryzen 9 9950X)")
    print("=" * 60)


if __name__ == "__main__":
    build_index()