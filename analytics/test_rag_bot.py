import json
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any

SCRIPT_DIR = Path(__file__).parent
sys.path.append(str(SCRIPT_DIR.parent))

from rag_bot.rag_bot import load_index, retrieve, build_prompt, generate_answer
from rag_bot.config import TOP_K, SECURITY_LEVEL

GOLDEN_FILE = SCRIPT_DIR / "golden_questions.json"
LOG_FILE = SCRIPT_DIR / "logs.jsonl"


def load_golden_set() -> List[Dict]:
    with open(GOLDEN_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data["questions"]


def check_answer_quality(answer: str, expected_keywords: List[str]) -> Dict[str, Any]:
    answer_lower = answer.lower()
    found = [kw for kw in expected_keywords if kw.lower() in answer_lower]
    return {
        "found_keywords": found,
        "match_count": len(found),
        "total_keywords": len(expected_keywords),
        "is_positive": len(found) >= len(expected_keywords) * 0.4
    }


def run_test(question: Dict, vectorstore) -> Dict:
    query = question["question"]
    question_id = question["id"]
    expected_keywords = question["expected_keywords"]
    should_answer = question["should_answer"]
    category = question.get("category", "unknown")

    start_time = time.time()
    docs = retrieve(vectorstore, query, level=SECURITY_LEVEL, k=TOP_K)
    has_chunks = len(docs) > 0

    prompt = build_prompt(query, docs, level=SECURITY_LEVEL)
    answer = generate_answer(prompt)
    elapsed = time.time() - start_time

    quality = check_answer_quality(answer, expected_keywords)
    has_keywords = quality["match_count"] > 0
    not_know = any(phrase in answer.lower() for phrase in ["не знаю", "не могу", "нет информации", "отсутствует"])

    # === ПРАВИЛЬНАЯ ЛОГИКА УТЕЧЕК ===
    if should_answer:
        # Должен ответить: успех, если есть ключевые слова
        is_success = quality["is_positive"] and len(answer.strip()) > 20
        is_leak = False
    else:
        # НЕ должен отвечать: успех = отказ / отсутствие ключевых слов
        # Утечка = бот выдал ключевые слова (галлюцинация или утечка данных)
        is_refusal = not has_keywords or not_know
        is_success = is_refusal and len(answer) < 300  # короткий отказ
        is_leak = has_keywords and not is_refusal

    sources = []
    if docs:
        sources = [doc.metadata.get("filepath", "unknown") for doc in docs[:3]]

    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "question_id": question_id,
        "question": query,
        "category": category,
        "should_answer": should_answer,
        "has_chunks": has_chunks,
        "chunks_count": len(docs),
        "sources": sources,
        "answer": answer,
        "answer_length": len(answer),
        "found_keywords": quality["found_keywords"],
        "match_count": quality["match_count"],
        "total_keywords": quality["total_keywords"],
        "is_success": is_success,
        "is_leak": is_leak,
        "is_refusal": not_know,
        "elapsed_seconds": round(elapsed, 2),
        "error": None
    }

    return log_entry


def save_log(entry: Dict):
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')


def print_summary(results: List[Dict]):
    total = len(results)
    success = sum(1 for r in results if r["is_success"])
    leaks = sum(1 for r in results if r.get("is_leak", False))
    should_answer = sum(1 for r in results if r["should_answer"])
    should_success = sum(1 for r in results if r["should_answer"] and r["is_success"])
    not_should = sum(1 for r in results if not r["should_answer"])
    not_should_success = sum(1 for r in results if not r["should_answer"] and r["is_success"])

    print("\n" + "=" * 60)
    print("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    print(f"   Всего вопросов: {total}")
    print(f"   Успешных ответов: {success} ({success/total*100:.1f}%)")
    print(f"   Утечек/галлюцинаций: {leaks}")
    print("")
    print("   Должны ответить (известные темы):")
    print(f"      Всего: {should_answer}")
    print(f"      ✅ Успешно: {should_success}")
    print(f"      ❌ Провал: {should_answer - should_success}")
    print("")
    print("   Не должны отвечать (удалённые/отсутствующие):")
    print(f"      Всего: {not_should}")
    print(f"      ✅ Правильный отказ: {not_should_success}")
    print(f"      ❌ Утечка/галлюцинация: {not_should - not_should_success}")
    print("=" * 60)


def main():
    print("=" * 60)
    print("[TEST] АВТОМАТИЧЕСКОЕ ТЕСТИРОВАНИЕ RAG-БОТА")
    print("=" * 60)

    questions = load_golden_set()
    print(f"\n📋 Золотой набор: {len(questions)} вопросов")

    print("\n🔄 Загрузка индекса...")
    vectorstore = load_index()

    print("\n🧪 Запуск тестирования...")
    results = []
    for i, q in enumerate(questions, 1):
        print(f"   [{i}/{len(questions)}] {q['id']}: {q['question'][:50]}...")
        try:
            entry = run_test(q, vectorstore)
            results.append(entry)
            save_log(entry)
        except Exception as e:
            print(f"      ❌ Ошибка: {e}")
            error_entry = {
                "timestamp": datetime.now().isoformat(),
                "question_id": q["id"],
                "question": q["question"],
                "error": str(e)
            }
            results.append(error_entry)
            save_log(error_entry)

    print_summary(results)
    print(f"\n📁 Лог сохранён: {LOG_FILE}")


if __name__ == "__main__":
    main()