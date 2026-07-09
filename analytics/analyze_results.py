import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Any

SCRIPT_DIR = Path(__file__).parent
LOG_FILE = SCRIPT_DIR / "logs.jsonl"
REPORT_FILE = SCRIPT_DIR / "coverage_report.md"


def load_logs() -> List[Dict]:
    logs = []
    if not LOG_FILE.exists():
        return logs
    with open(LOG_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                logs.append(json.loads(line))
    return logs


def analyze(logs: List[Dict]) -> Dict[str, Any]:
    total = len(logs)
    errors = sum(1 for l in logs if l.get("error"))
    success = sum(1 for l in logs if l.get("is_success", False))
    leaks = sum(1 for l in logs if l.get("is_leak", False))
    no_chunks = [l for l in logs if not l.get("has_chunks", True) and not l.get("error")]
    low_quality = [l for l in logs if not l.get("is_success") and not l.get("error") and l.get("should_answer")]
    hallucinations = [l for l in logs if l.get("is_leak")]

    by_category = defaultdict(lambda: {"total": 0, "success": 0, "should_answer": 0})
    for l in logs:
        cat = l.get("category", "unknown")
        by_category[cat]["total"] += 1
        if l.get("is_success"):
            by_category[cat]["success"] += 1
        if l.get("should_answer"):
            by_category[cat]["should_answer"] += 1

    return {
        "total": total,
        "errors": errors,
        "success": success,
        "leaks": leaks,
        "success_rate": success / total * 100 if total > 0 else 0,
        "by_category": dict(by_category),
        "no_chunks": no_chunks,
        "low_quality": low_quality,
        "hallucinations": hallucinations,
        "logs": logs
    }


def generate_report(analysis: Dict[str, Any]) -> str:
    lines = []
    lines.append("# Отчёт о покрытии и качестве базы знаний")
    lines.append("")
    lines.append(f"**Дата:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("## 📊 Общая статистика")
    lines.append("")
    lines.append(f"| Параметр | Значение |")
    lines.append(f"|----------|----------|")
    lines.append(f"| Всего запросов | {analysis['total']} |")
    lines.append(f"| Успешных ответов | {analysis['success']} ({analysis['success_rate']:.1f}%) |")
    lines.append(f"| Утечек/галлюцинаций | {analysis['leaks']} |")
    lines.append(f"| Ошибок выполнения | {analysis['errors']} |")
    lines.append("")

    lines.append("## 📂 Результаты по категориям")
    lines.append("")
    lines.append(f"| Категория | Всего | Успешно | Должны ответить |")
    lines.append(f"|-----------|-------|---------|-----------------|")
    for cat, stats in analysis["by_category"].items():
        lines.append(f"| {cat} | {stats['total']} | {stats['success']} | {stats['should_answer']} |")
    lines.append("")

    lines.append("## ⚠️ Пробелы в покрытии")
    lines.append("")
    if analysis["no_chunks"]:
        lines.append("### ❌ Вопросы без найденных чанков")
        for l in analysis["no_chunks"]:
            lines.append(f"- `{l['question']}` — источники не найдены (категория: {l.get('category', 'unknown')})")
    else:
        lines.append("✅ Все вопросы нашли хотя бы один чанк.")
    lines.append("")

    if analysis["low_quality"]:
        lines.append("### ⚠️ Вопросы с низким качеством ответа")
        for l in analysis["low_quality"]:
            lines.append(f"- `{l['question']}` — найдено ключевых слов: {l.get('match_count', 0)}/{l.get('total_keywords', 0)}")
    else:
        lines.append("✅ Все ответы содержат ключевые слова.")
    lines.append("")

    if analysis["hallucinations"]:
        lines.append("### 🔴 Утечки данных / галлюцинации")
        for l in analysis["hallucinations"]:
            lines.append(f"- `{l['question']}` — бот выдал информацию, хотя должен был отказаться (категория: {l.get('category', 'unknown')})")
    else:
        lines.append("✅ Нет утечек данных.")
    lines.append("")

    lines.append("## 💡 Рекомендации по улучшению")
    lines.append("")
    if analysis["no_chunks"]:
        lines.append("### Расширить базу знаний")
        for l in analysis["no_chunks"]:
            lines.append(f"- Добавить информацию по запросу: «{l['question']}»")
    if analysis["low_quality"]:
        lines.append("### Улучшить качество ответов")
        lines.append("- Добавить больше релевантных чанков")
        lines.append("- Увеличить `TOP_K` для поиска (сейчас 5)")
        lines.append("- Добавить переранжирование (reranking) результатов")
    if analysis["hallucinations"]:
        lines.append("### Усилить защиту от галлюцинаций")
        lines.append("- Улучшить системный промпт (pre‑prompt)")
        lines.append("- Добавить пост-фильтрацию ответов на «неизвестные» темы")
        lines.append("- Добавить порог уверенности для отказа от ответа")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Отчёт сгенерирован автоматически.*")
    return "\n".join(lines)


def main():
    print("=" * 60)
    print("[ANALYZE] АНАЛИЗ ЛОГОВ И ГЕНЕРАЦИЯ ОТЧЁТА")
    print("=" * 60)

    logs = load_logs()
    if not logs:
        print("❌ Нет данных для анализа. Сначала запустите test_rag_bot.py")
        return

    print(f"📂 Загружено записей: {len(logs)}")
    analysis = analyze(logs)
    report = generate_report(analysis)

    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"✅ Отчёт сохранён: {REPORT_FILE}")
    print("\n" + "=" * 60)
    print("📊 СВОДКА")
    print("=" * 60)
    print(f"   Всего: {analysis['total']}")
    print(f"   Успешно: {analysis['success']} ({analysis['success_rate']:.1f}%)")
    print(f"   Утечек/галлюцинаций: {analysis['leaks']}")
    print(f"   Пробелов (нет чанков): {len(analysis['no_chunks'])}")


if __name__ == "__main__":
    main()