# Задание 2. Подготовка базы знаний

## Описание проекта

Создана уникальная база знаний на основе вселенной Star Wars с заменой ключевых терминов на вымышленные названия. Это гарантирует, что LLM не сможет ответить по памяти, а будет использовать только загруженные документы.

Исходная вселенная: Star Wars
Новая вселенная: Khroniki Mezhdumirya  
Источник: [Wookieepedia](https://starwars.fandom.com)

## Структура проекта

```
knowledge_base/
├── downloads/          # Сырые HTML-страницы
├── clear/              # Очищенные тексты
├── final/              # Итоговые документы (после замены)
├── links.json          # Список URL для скачивания
├── terms_map.json      # Словарь замен
├── download_and_clean.py
├── replace_terms.py
└── README.md
```

## Словарь замен (`terms_map.json`)

Содержит более 400 замен по категориям:

| Категория   | Количество |
|-------------|------------|
| Персонажи   | 80+        |
| Планеты     | 50+        |
| Технологии  | 60+        |
| Расы        | 40+        |
| Организации | 50+        |
| События     | 30+        |
| Локации     | 30+        |

Примеры замен:

| Оригинал          | Замена (Khroniki Mezhdumirya) |
|-------------------|-------------------------------|
| Luke Skywalker    | Ivan Nebov                    |
| Darth Vader       | Semyon Tyomnov                |
| Han Solo          | Alexey Odinokov               |
| Chewbacca         | Mikhail Medvedev              |
| Tatooine          | Sukhostep                     |
| Coruscant         | Stolny Grad                   |
| Hoth              | Morozgrad                     |
| Death Star        | Zvezda Smerti                 |
| Lightsaber        | Svetomech                     |
| Blaster           | Luchemyot                     |
| The Force         | Sila                          |
| Jedi Order        | Orden Vedunov                 |
| Sith Order        | Bratstvo Temnikov             |
| Galactic Empire   | Vselennaya Derzhava           |
| Rebel Alliance    | Volny Soyuz                   |

## Установка

```bash
pip install requests beautifulsoup4
```

## Использование

### 1. Скачивание и очистка

```bash
python download_and_clean.py
```

### 2. Замена терминов

```bash
python replace_terms.py
```

## Итоговые документы (`final/`)

30+ документов в категориях:

- `characters/` - Ivan Nebov, Semyon Tyomnov, Olga Knyazeva, Alexey Odinokov и др.
- `planets/` - Sukhostep, Stolny Grad, Morozgrad, Lesnogorsk и др.
- `technologies/` - Svetomech, Zvezda Smerti, Zvezdoplyot, Luchemyot и др.
- `organizations/` - Orden Vedunov, Bratstvo Temnikov, Vselennaya Derzhava и др.
- `events/` - Bitva pri Zelyonoy Lune, Bitva v Lesnogorske, Bliznetsovy Voyny и др.

