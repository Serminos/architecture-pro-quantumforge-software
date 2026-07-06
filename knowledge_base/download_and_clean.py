import os
import json
import re
import html
import requests
from bs4 import BeautifulSoup
from pathlib import Path


def load_links(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def clean_final_text(text):
    """Финальная очистка текста."""
    # Убираем пробелы перед знаками препинания
    text = re.sub(r'\s+([.,;:!?"\'—])', r'\1', text)
    # Убираем пробелы после открывающих кавычек
    text = re.sub(r'(["\'])\s+', r'\1', text)
    # Убираем пробелы перед закрывающими кавычками
    text = re.sub(r'\s+(["\'])', r'\1', text)
    # Убираем пробелы вокруг дефисов в составных словах (например, "Firespray-31 -class" → "Firespray-31-class")
    text = re.sub(r'(\w+)\s*-\s*(\w+)', r'\1-\2', text)
    # Убираем множественные пробелы
    text = re.sub(r' +', ' ', text)
    # Убираем пустые строки
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return '\n'.join(lines)


def extract_main_text(html_content):
    """Извлекает только основной текст статьи, удаляя все служебные блоки."""
    soup = BeautifulSoup(html_content, 'html.parser')

    # Удаляем скрипты, стили, навигацию, рекламу
    for element in soup(['script', 'style', 'noscript', 'iframe', 'svg', 'meta', 'link']):
        element.decompose()
    for element in soup.find_all(['nav', 'header', 'footer', 'aside', 'form']):
        element.decompose()

    classes_to_remove = [
        'nav', 'navbar', 'navigation', 'sidebar', 'ad', 'advertisement',
        'banner', 'promo', 'popup', 'modal', 'cookie', 'menu',
        'toolbar', 'share', 'social', 'comments', 'sitenotice',
        'notifications-placeholder', 'global-top-navigation',
        'community-navigation', 'global-explore-navigation',
        'right-rail-wrapper', 'global-footer', 'page-footer',
        'mw-editsection', 'thumb', 'quote', 'reference',
        'scrollbox', 'cardgame', 'hidable', 'conflict-navbox'
    ]
    for class_name in classes_to_remove:
        for element in soup.find_all(class_=class_name):
            element.decompose()
        for element in soup.find_all(id=class_name):
            element.decompose()

    for table in soup.find_all('table', class_='navbox'):
        table.decompose()
    for div in soup.find_all('div', class_='quote'):
        div.decompose()

    # Находим основной контент
    content = soup.find('div', class_='mw-parser-output')
    if not content:
        for selector in ['#content', '.article-content', '.main-content', '.mw-body-content']:
            content = soup.select_one(selector)
            if content:
                break
    if not content:
        return None

    # Удаляем всё до первого абзаца
    first_p = content.find('p')
    if first_p:
        for elem in list(content.children):
            if elem == first_p:
                break
            elem.decompose()

    # Удаляем всё, начиная с разделов Appearances/Sources
    stop_markers = ['Appearances', 'Sources', 'Notes and references', 'In other languages']
    for header in content.find_all(['h2', 'h3']):
        header_text = header.get_text(strip=True)
        if any(marker in header_text for marker in stop_markers):
            for elem in list(header.find_all_next()):
                elem.decompose()
            header.decompose()
            break

    # Удаляем пустые теги
    for tag in content.find_all():
        if not tag.get_text(strip=True) and not tag.find_all():
            tag.decompose()

    # Получаем текст с разделителем \n
    raw_text = content.get_text(separator='\n')

    # Разбиваем на абзацы (по двойным переносам)
    paragraphs = [p.strip() for p in raw_text.split('\n\n') if p.strip()]
    # Внутри каждого абзаца заменяем переносы строк на пробелы
    paragraphs = [' '.join(p.splitlines()) for p in paragraphs]
    # Объединяем абзацы одинарным переносом
    clean_text = '\n'.join(paragraphs)

    # Декодируем HTML-сущности
    clean_text = html.unescape(clean_text)

    # Удаляем строки с служебными фразами
    skip_phrases = [
        'Content approaching.', 'Please update the article',
        'In other languages', 'Community content is available under',
        'Sci-fi', 'Star Wars', 'Wookieepedia',
        'Sign In', 'Don\'t have an account?', 'Create a Free Account',
        'READ MORE', 'Advertisement', 'Skip to content',
        'Edit source', 'History', 'Purge', 'Talk',
        'Save', 'Share', 'Categories', 'Previous', 'Next',
        'Conflict', 'Date', 'Place', 'Outcome', 'Combatants', 'Commanders'
    ]
    lines = clean_text.splitlines()
    filtered_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(phrase in line for phrase in skip_phrases):
            continue
        if re.match(r'^\[\d+\]', line) or re.match(r'^↑ \d+\.\d+', line):
            continue
        filtered_lines.append(line)

    clean_text = '\n'.join(filtered_lines)

    # Финальная очистка
    clean_text = clean_final_text(clean_text)

    return clean_text


def process_links(links, download_dir, clear_dir):
    """Обрабатывает все ссылки: скачивает и очищает."""
    stats = {'total': 0, 'downloaded': 0, 'cleaned': 0, 'errors': 0}

    for category, items in links.items():
        dl_cat_path = Path(download_dir) / category
        cl_cat_path = Path(clear_dir) / category
        dl_cat_path.mkdir(parents=True, exist_ok=True)
        cl_cat_path.mkdir(parents=True, exist_ok=True)

        print(f"\nОбработка категории: {category} ({len(items)} страниц)")

        for item in items:
            name = item['name']
            url = item['url']
            stats['total'] += 1

            html_path = dl_cat_path / f"{name}.html"

            if not html_path.exists():
                try:
                    headers = {
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    }
                    response = requests.get(url, headers=headers, timeout=15)
                    response.raise_for_status()
                    with open(html_path, 'w', encoding='utf-8') as f:
                        f.write(response.text)
                    print(f"  Скачано: {name}")
                    stats['downloaded'] += 1
                except Exception as e:
                    print(f"  Ошибка скачивания {name}: {e}")
                    stats['errors'] += 1
                    continue
            else:
                print(f"  Уже скачано: {name}")

            try:
                with open(html_path, 'r', encoding='utf-8') as f:
                    html = f.read()

                clean_text = extract_main_text(html)

                if clean_text and len(clean_text) > 100:
                    txt_path = cl_cat_path / f"{name}.txt"
                    with open(txt_path, 'w', encoding='utf-8') as f:
                        f.write(clean_text)
                    print(f"  Очищено: {txt_path}")
                    stats['cleaned'] += 1
                else:
                    print(f"  Текст слишком короткий: {name}")
                    stats['errors'] += 1

            except Exception as e:
                print(f"  Ошибка очистки {name}: {e}")
                stats['errors'] += 1

    return stats


def main():
    base_dir = Path(__file__).parent
    links_file = base_dir / "links.json"
    download_dir = base_dir / "downloads"
    clear_dir = base_dir / "clear"

    if not links_file.exists():
        print("Файл links.json не найден!")
        return

    print("Запуск скачивания и очистки документов...")
    print("=" * 60)

    with open(links_file, 'r', encoding='utf-8') as f:
        links = json.load(f)

    stats = process_links(links, download_dir, clear_dir)

    print("\n" + "=" * 60)
    print("СТАТИСТИКА:")
    print(f"  Всего страниц: {stats['total']}")
    print(f"  Скачано: {stats['downloaded']}")
    print(f"  Очищено: {stats['cleaned']}")
    print(f"  Ошибок: {stats['errors']}")

    if stats['cleaned'] > 0:
        print("\nГотово! Очищенные тексты сохранены в папке clear/")
    else:
        print("\nНе удалось очистить ни одного документа. Проверьте links.json")


if __name__ == "__main__":
    main()