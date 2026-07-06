import json
import re
import os
from pathlib import Path


def load_terms(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def replace_terms_in_text(text, terms_map):
    all_terms = {}
    for category in ['characters', 'planets', 'technologies', 'organizations', 'events', 'races_species',
                     'concepts_organizations', 'locations', 'weapons', 'ships', 'misc']:
        if category in terms_map:
            all_terms.update(terms_map[category])

    # Сортируем по убыванию длины (сначала длинные фразы)
    sorted_terms = sorted(all_terms.items(), key=lambda x: len(x[0]), reverse=True)

    for original, replacement in sorted_terms:
        text = text.replace(original, replacement)

    return text


def process_clear_to_final(clear_dir, final_dir, terms_map):
    """Копирует файлы из clear в final, заменяя термины."""
    clear_path = Path(clear_dir)
    final_path = Path(final_dir)

    for category in os.listdir(clear_path):
        cat_clear = clear_path / category
        if not cat_clear.is_dir():
            continue
        cat_final = final_path / category
        cat_final.mkdir(parents=True, exist_ok=True)

        for file in cat_clear.glob("*.txt"):
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content = replace_terms_in_text(content, terms_map)

            # Сохраняем в final
            output_file = cat_final / file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Обработан: {output_file}")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    terms_file = base_dir / "terms_map.json"
    clear_dir = base_dir / "clear"
    final_dir = base_dir / "final"

    if not terms_file.exists():
        print("terms_map.json не найден!")
        exit(1)
    if not clear_dir.exists():
        print("Папка clear/ не найдена! Сначала запустите download_and_clean.py")
        exit(1)

    terms = load_terms(terms_file)
    process_clear_to_final(clear_dir, final_dir, terms)
    print("!!! Замена терминов завершена. Итоговые документы в папке final/")