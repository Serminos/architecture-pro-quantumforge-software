import hashlib
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Добавляем пути для импорта модулей проекта
SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR.parent / "vector_index"))
sys.path.append(str(SCRIPT_DIR.parent / "knowledge_base"))

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

from vector_index.build_index import chunk_documents, MODEL_NAME
from knowledge_base.download_and_clean import extract_main_text

# ========== КОНФИГУРАЦИЯ ==========
INCOMING_DIR = SCRIPT_DIR.parent / "knowledge_base" / "incoming"
PROCESSED_DIR = SCRIPT_DIR.parent / "knowledge_base" / "processed"
INDEX_DIR = SCRIPT_DIR.parent / "vector_index" / "indices" / "faiss_index"
LOG_FILE = SCRIPT_DIR / "update_log.json"

# ========== ФУНКЦИИ ==========

def setup_directories():
    """Создаёт необходимые папки."""
    INCOMING_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    INDEX_DIR.mkdir(parents=True, exist_ok=True)

def get_file_hash(file_path: Path) -> str:
    """MD5-хеш файла."""
    return hashlib.md5(file_path.read_bytes()).hexdigest()

def load_processed_files() -> Dict[str, str]:
    """Загружает словарь обработанных файлов {имя: хеш} из лога."""
    if not LOG_FILE.exists():
        return {}
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        try:
            logs = json.load(f)
        except json.JSONDecodeError:
            return {}
    processed = {}
    for entry in logs:
        for file_info in entry.get("files", []):
            processed[file_info["name"]] = file_info["hash"]
    return processed

def find_new_files() -> List[Path]:
    """Находит новые или изменённые файлы в incoming/."""
    processed = load_processed_files()
    new_files = []
    for file_path in INCOMING_DIR.glob("*"):
        if file_path.is_file():
            file_hash = get_file_hash(file_path)
            if file_path.name not in processed or processed[file_path.name] != file_hash:
                new_files.append(file_path)
    return new_files

def load_documents_from_files(file_paths: List[Path]) -> List[Document]:
    """
    Загружает документы из файлов.
    Для .txt читает как есть.
    Для .html использует extract_main_text из download_and_clean.py.
    """
    documents = []
    for file_path in file_paths:
        try:
            if file_path.suffix.lower() == ".html":
                html_content = file_path.read_text(encoding="utf-8")
                content = extract_main_text(html_content)
                if not content or len(content.strip()) < 10:
                    continue
            else:
                content = file_path.read_text(encoding="utf-8")
                if len(content.strip()) < 10:
                    continue

            doc = Document(
                page_content=content,
                metadata={
                    "source": str(file_path),
                    "filename": file_path.stem,
                    "category": "incoming",
                    "updated_at": datetime.now().isoformat()
                }
            )
            documents.append(doc)
        except Exception as e:
            print(f"  [ERROR] Ошибка загрузки {file_path.name}: {e}")
    return documents

def load_existing_index() -> FAISS:
    """Загружает существующий FAISS-индекс."""
    embeddings = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 16}
    )
    index_file = INDEX_DIR / "index.faiss"
    if not index_file.exists():
        print("[WARN] Индекс не найден. Будет создан новый.")
        return None
    vectorstore = FAISS.load_local(
        str(INDEX_DIR),
        embeddings,
        allow_dangerous_deserialization=True
    )
    print(f"[OK] Индекс загружен. Размер: {vectorstore.index.ntotal} чанков")
    return vectorstore

def get_index_size(vectorstore: FAISS) -> int:
    """Возвращает количество чанков в индексе."""
    try:
        return vectorstore.index.ntotal
    except AttributeError:
        return len(vectorstore.docstore._dict)

def update_index(vectorstore: FAISS, new_chunks: List[Document]) -> FAISS:
    """Добавляет новые чанки в индекс (создаёт новый, если индекса нет)."""
    if vectorstore is None:
        print("  [WARN] Создаём новый индекс...")
        embeddings = HuggingFaceEmbeddings(
            model_name=MODEL_NAME,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True, "batch_size": 16}
        )
        vectorstore = FAISS.from_documents(
            documents=new_chunks,
            embedding=embeddings
        )
    else:
        print(f"  [ADD] Добавляем {len(new_chunks)} чанков...")
        vectorstore.add_documents(new_chunks)
    return vectorstore

def move_to_processed(file_paths: List[Path]):
    """Перемещает обработанные файлы в processed/."""
    for file_path in file_paths:
        dest = PROCESSED_DIR / file_path.name
        shutil.move(str(file_path), str(dest))
        print(f"  [MOVE] Перемещён: {file_path.name} -> processed/")

def write_log(files_info: List[Dict], chunks_added: int, index_size: int, errors: List[str]):
    """
    Добавляет запись в JSON-лог.
    files_info: список словарей с ключами name, hash, size_kb.
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "files": files_info,
        "chunks_added": chunks_added,
        "index_size": index_size,
        "errors": errors
    }
    if LOG_FILE.exists():
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            try:
                logs = json.load(f)
            except json.JSONDecodeError:
                logs = []
    else:
        logs = []
    logs.append(log_entry)
    if len(logs) > 100:
        logs = logs[-100:]
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def main():
    print("=" * 60)
    print("[UPDATE] ОБНОВЛЕНИЕ ВЕКТОРНОГО ИНДЕКСА")
    print(f"   Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    start_time = time.time()
    errors = []
    files_info = []
    chunks_added = 0

    try:
        setup_directories()

        # 1. Поиск новых файлов
        print("\n[STEP 1] Поиск новых файлов...")
        new_files = find_new_files()
        print(f"   Найдено: {len(new_files)}")
        if not new_files:
            print("   [OK] Новых файлов нет.")
            return

        # Сохраняем информацию о файлах до перемещения
        for f in new_files:
            files_info.append({
                "name": f.name,
                "hash": get_file_hash(f),
                "size_kb": round(f.stat().st_size / 1024, 2)
            })

        # 2. Загрузка документов
        print("\n[STEP 2] Загрузка документов...")
        docs = load_documents_from_files(new_files)
        print(f"   Загружено: {len(docs)}")
        if not docs:
            print("   [WARN] Нет загружаемых документов.")
            move_to_processed(new_files)
            write_log(files_info, 0, 0, ["No loadable documents"])
            return

        # 3. Чанкинг
        print("\n[STEP 3] Разбивка на чанки...")
        chunks = chunk_documents(docs)
        chunks_added = len(chunks)
        print(f"   Создано чанков: {chunks_added}")

        # 4. Загрузка индекса
        print("\n[STEP 4] Загрузка индекса...")
        vectorstore = load_existing_index()
        old_size = get_index_size(vectorstore) if vectorstore else 0

        # 5. Обновление индекса
        print("\n[STEP 5] Обновление индекса...")
        vectorstore = update_index(vectorstore, chunks)

        # 6. Сохранение индекса
        print("\n[STEP 6] Сохранение индекса...")
        vectorstore.save_local(str(INDEX_DIR))

        # 7. Перемещение файлов
        print("\n[STEP 7] Перемещение обработанных...")
        move_to_processed(new_files)

        # 8. Логирование
        new_size = get_index_size(vectorstore)
        print("\n[STEP 8] Логирование...")
        write_log(files_info, chunks_added, new_size, errors)

        # 9. Статистика
        elapsed = time.time() - start_time
        print("\n" + "=" * 60)
        print("[STATS] СТАТИСТИКА ОБНОВЛЕНИЯ")
        print("=" * 60)
        print(f"   Добавлено файлов: {len(files_info)}")
        print(f"   Добавлено чанков: {chunks_added}")
        print(f"   Размер индекса: {new_size} чанков")
        print(f"   Время: {elapsed:.2f} сек")
        print(f"   Ошибок: {len(errors)}")
        print("=" * 60)
        print("[OK] Индекс успешно обновлён!")

    except Exception as e:
        print(f"\n[ERROR] КРИТИЧЕСКАЯ ОШИБКА: {e}")
        errors.append(f"CRITICAL: {str(e)}")
        write_log(files_info, chunks_added, 0, errors)

if __name__ == "__main__":
    main()