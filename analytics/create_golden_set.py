import json
import shutil
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
KNOWLEDGE_BASE_DIR = SCRIPT_DIR.parent / "knowledge_base" / "final"
BACKUP_DIR = SCRIPT_DIR.parent / "knowledge_base" / "backup_gaps"

# Файлы, которые нужно удалить для создания пробелов
# (реальные файлы, существующие в вашей базе знаний)
FILES_TO_REMOVE = [
    # Удаляем один из файлов персонажей, например, про "Starik Vseslavov" (Obi-Wan Kenobi)
    "characters/obi_wan_kenobi.txt",
    # Удаляем одну из планет, например, "Aquaria" (Naboo)
    "planets/naboo.txt",
    # Удаляем одну из технологий, например, "Giperprivod" (Hyperdrive)
    "technologies/hyperdrive.txt",
]


def create_golden_set():
    """Создаёт JSON с золотым набором вопросов."""
    golden_set = {
        "metadata": {
            "description": "Золотой набор вопросов для оценки RAG-бота",
            "version": "2.0",
            "created": "2026-07-06"
        },
        "questions": [
            # ========== Вопросы на известные темы (8 шт.) ==========
            {
                "id": "Q001",
                "question": "Кто такой Ivan Nebov?",
                "expected_keywords": ["Ivan Nebov", "главный герой", "мастер-ведун", "Sukhostep"],
                "should_answer": True,
                "category": "characters"
            },
            {
                "id": "Q002",
                "question": "Что такое Svetomech?",
                "expected_keywords": ["Svetomech", "оружие", "Ведунов", "плазма"],
                "should_answer": True,
                "category": "technologies"
            },
            {
                "id": "Q003",
                "question": "Где находится Sukhostep?",
                "expected_keywords": ["Sukhostep", "планета", "Outer Rim", "пустынная"],
                "should_answer": True,
                "category": "planets"
            },
            {
                "id": "Q004",
                "question": "Что такое Orden Vedunov?",
                "expected_keywords": ["Orden Vedunov", "орден", "Ведуны", "монашеский"],
                "should_answer": True,
                "category": "organizations"
            },
            {
                "id": "Q005",
                "question": "Что произошло в Bitva pri Zelyonoy Lune?",
                "expected_keywords": ["Zelyonoy Lune", "битва", "Zvezda Smerti", "Volny Soyuz"],
                "should_answer": True,
                "category": "events"
            },
            {
                "id": "Q006",
                "question": "Кто такой Semyon Tyomnov?",
                "expected_keywords": ["Semyon Tyomnov", "антагонист", "Tyomnaya Storona", "Vselennaya Derzhava"],
                "should_answer": True,
                "category": "characters"
            },
            {
                "id": "Q007",
                "question": "Что такое Zvezda Smerti?",
                "expected_keywords": ["Zvezda Smerti", "супероружие", "уничтожена", "Bitva"],
                "should_answer": True,
                "category": "technologies"
            },
            {
                "id": "Q008",
                "question": "Кто такая Olga Knyazeva?",
                "expected_keywords": ["Olga Knyazeva", "принцесса", "Volny Soyuz"],
                "should_answer": True,
                "category": "characters"
            },

            # ========== Вопросы на удалённые/отсутствующие темы (5 шт.) ==========
            {
                "id": "Q009",
                "question": "Кто такой Starik Vseslavov?",
                "expected_keywords": ["Starik Vseslavov", "учитель", "Оби-Ван"],
                "should_answer": False,
                "category": "characters",
                "note": "УДАЛЁН — файл starik_vseslavov.txt удалён"
            },
            {
                "id": "Q010",
                "question": "Где находится Aquaria?",
                "expected_keywords": ["Aquaria", "планета", "вода"],
                "should_answer": False,
                "category": "planets",
                "note": "УДАЛЁН — файл aquaria.txt удалён"
            },
            {
                "id": "Q011",
                "question": "Что такое Giperprivod?",
                "expected_keywords": ["Giperprivod", "гиперпривод", "двигатель"],
                "should_answer": False,
                "category": "technologies",
                "note": "УДАЛЁН — файл giperprivod.txt удалён"
            },
            {
                "id": "Q012",
                "question": "Кто такой Petr Smelchakov?",
                "expected_keywords": ["Petr Smelchakov"],
                "should_answer": False,
                "category": "characters",
                "note": "НЕ СУЩЕСТВУЕТ — персонаж не описан в базе"
            },
            {
                "id": "Q013",
                "question": "Что произошло v Bitve pri Moskva?",
                "expected_keywords": ["Moskva"],
                "should_answer": False,
                "category": "events",
                "note": "НЕ СУЩЕСТВУЕТ — событие не описано"
            }
        ]
    }

    output_path = SCRIPT_DIR / "golden_questions.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(golden_set, f, ensure_ascii=False, indent=2)
    print(f"✅ Золотой набор сохранён: {output_path}")


def create_gaps():
    """
    Физически удаляет файлы из базы знаний (создаёт пробелы).
    Сохраняет резервную копию в ../knowledge_base/backup_gaps/
    """
    print("\n🗑️  СОЗДАНИЕ ИСКУССТВЕННЫХ ПРОБЕЛОВ")
    print("=" * 60)

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    removed = []

    for rel_path in FILES_TO_REMOVE:
        source = KNOWLEDGE_BASE_DIR / rel_path
        if source.exists():
            backup = BACKUP_DIR / rel_path
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, backup)
            source.unlink()
            removed.append(rel_path)
            print(f"🗑️  Удалён: {rel_path}")
        else:
            print(f"⚠️  Файл не найден (пропускаем): {rel_path}")

    if removed:
        print("\n📦 Резервные копии сохранены в:")
        print(f"   {BACKUP_DIR}")
        print("\n⚠️  НЕ ЗАБУДЬТЕ ПЕРЕСТРОИТЬ ИНДЕКС:")
        print("   cd ../vector_index")
        print("   python build_index.py")
    else:
        print("\n⚠️  Ни один файл не удалён. Проверьте пути в FILES_TO_REMOVE.")


def main():
    print("=" * 60)
    print("[CREATE] СОЗДАНИЕ ЗОЛОТОГО НАБОРА И ПРОБЕЛОВ")
    print("=" * 60)

    create_golden_set()
    create_gaps()

    print("\n✅ Готово! Следующие шаги:")
    print("   1. Перестройте индекс: cd ../vector_index && python build_index.py")
    print("   2. Запустите тестирование: cd ../analytics && python test_rag_bot.py")
    print("   3. Проанализируйте: python analyze_results.py")


if __name__ == "__main__":
    main()