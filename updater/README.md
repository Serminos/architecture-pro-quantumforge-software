# Задание 6. Автоматическое обновление базы знаний

## Описание

Реализован автоматический пайплайн ежедневного обновления векторного индекса. Новые документы добавляются в папку `knowledge_base/incoming/`, скрипт `update_index.py` обрабатывает их и добавляет в FAISS-индекс.

## Архитектура

![update_flow.png](schema/update_flow.png)

[update_flow.puml](schema/update_flow.puml)

## Структура проекта
| Файл                                   | Описание                             |
|----------------------------------------|--------------------------------------|
| `updater/update_index.py`              | Основной скрипт обновления индекса   |
| `updater/update_index.bat`             | Запуск для Windows (планировщик)     |
| `updater/update_log.json`              | Структурированный лог в формате JSON |
| `updater/update_log.txt`               | Текстовый лог для отладки            |
| `../schema/update_flow.png`            | Диаграмма архитектуры                |
| `../schema/update_flow.puml`           | PlantUML-диаграмма                   |
| `../knowledge_base/incoming/`          | Папка для новых файлов               |
| `../knowledge_base/processed/`         | Папка для обработанных файлов        |
| `../vector_index/indices/faiss_index/` | Обновляемый индекс                   |


## Установка и настройка

### 1. Установка зависимостей
```bash
pip install -r ..\requirements.txt
```

## Использование

### Ручной запуск

```bash
cd updater
python update_index.py
```

### Или через `.bat` файл

Файл `update_index.bat` уже настроен. При необходимости отредактируйте пути:

```batch
@echo off
cd /d "D:\GITOfficial\architecture-pro-quantumforge-software\updater"
"D:\GITOfficial\architecture-pro-quantumforge-software\.venv\Scripts\python.exe" update_index.py >> update_log.txt 2>&1
```

### Автоматический запуск (Windows Task Scheduler)

1. Откройте `taskschd.msc`
2. Создайте задачу с триггером "Ежедневно" (например, в 20:10)
3. Действие: запуск `update_index.bat`
4. Рабочая папка: `D:\GITOfficial\architecture-pro-quantumforge-software\updater`

Или выполните add_sheduler.ps1 в PowerShell
```powershell
@echo off
cd /d "D:\GITOfficial\architecture-pro-quantumforge-software\updater"
.\add_sheduler.ps1
```

## Логирование

### Формат `update_log.json`

```json
[
  {
    "timestamp": "2026-07-06T21:51:30.284591",
    "files": [
      {
        "name": "Aurra Sing _ Wookieepedia _ Fandom.html",
        "hash": "cf32d437ce562f52409b72d7efa3e167",
        "size_kb": 573.89
      },
      {
        "name": "Krayt's Claw _ Wookieepedia _ Fandom.html",
        "hash": "f1d71a18e6efd90acd0974ecb25972b3",
        "size_kb": 375.97
      },
      {
        "name": "Teek _ Wookieepedia _ Fandom.html",
        "hash": "7770723f223e4fe5a92d27e22e532ffa",
        "size_kb": 352.38
      }
    ],
    "chunks_added": 29,
    "index_size": 3989,
    "errors": []
  }
]
```

### Пример текстового лога (`update_log.txt`)

```
D:\GITOfficial\architecture-pro-quantumforge-software\updater\update_index.py:17: DeprecationWarning: `langchain-community` is being sunset and is no longer actively maintained. See https://github.com/langchain-ai/langchain-community/issues/674 for details and migration guidance toward standalone integration packages.
  from langchain_community.vectorstores import FAISS
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
============================================================
[UPDATE] ОБНОВЛЕНИЕ ВЕКТОРНОГО ИНДЕКСА
   Время: 2026-07-06 21:55:03
============================================================

[STEP 1] Поиск новых файлов...
   Найдено: 3

[STEP 2] Загрузка документов...
   Загружено: 3

[STEP 3] Разбивка на чанки...
   Создано чанков: 29

[STEP 4] Загрузка индекса...

Loading weights:   0%|          | 0/391 [00:00<?, ?it/s]
Loading weights: 100%|##########| 391/391 [00:00<00:00, 63722.91it/s]
[OK] Индекс загружен. Размер: 3989 чанков

[STEP 5] Обновление индекса...
  [ADD] Добавляем 29 чанков...

[STEP 6] Сохранение индекса...

[STEP 7] Перемещение обработанных...
  [MOVE] Перемещён: Aurra Sing _ Wookieepedia _ Fandom.html -> processed/
  [MOVE] Перемещён: Krayt's Claw _ Wookieepedia _ Fandom.html -> processed/
  [MOVE] Перемещён: Teek _ Wookieepedia _ Fandom.html -> processed/

[STEP 8] Логирование...

============================================================
[STATS] СТАТИСТИКА ОБНОВЛЕНИЯ
============================================================
   Добавлено файлов: 3
   Добавлено чанков: 29
   Размер индекса: 4018 чанков
   Время: 13.86 сек
   Ошибок: 0
============================================================
[OK] Индекс успешно обновлён!

```

## Тестирование

1. Поместите любой `.txt` или `.html` файл в `../knowledge_base/incoming/`
2. Запустите `python update_index.py` из папки `updater/`
3. Проверьте:
   - Файл переместился в `../knowledge_base/processed/`
   - В `update_log.json` появилась новая запись
   - Индекс обновился (проверьте через `../vector_index/search_index.py`)

[Примеры логов с информацией после обновления](../saved_log/dialog_after_update.txt)

## Особенности
### Обработка HTML
Файлы с расширением `.html` автоматически очищаются через `extract_main_text()` из `../knowledge_base/download_and_clean.py`.
### Изменённые файлы
Файлы с тем же именем, но изменённым содержимым, обрабатываются как новые (по хешу MD5).