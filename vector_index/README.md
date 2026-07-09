## Задание 3. Векторный индекс базы знаний «Khroniki Mezhdumirya»

### Описание

Создан векторный индекс для семантического поиска в базе знаний на основе вселенной «Хроники Междумирья» (деякоризированная версия Star Wars с русскими терминами).

| Параметр           | Значение                                          |
|--------------------|---------------------------------------------------|
| Модель эмбеддингов | [BAAI/bge-m3](https://huggingface.co/BAAI/bge-m3) |
| Размерность        | 1024                                              |
| Векторная БД       | FAISS (CPU, IndexFlatL2)                          |
| Документов         | 40                                                |
| Чанков             | 3 836                                             |
| Размер чанка       | 1 536 символов                                    |
| Перекрытие         | 200 символов                                      |
| Устройство         | CPU (Ryzen 9 9950X)                               |
| Время индексации   | 806 сек (~13.4 мин)                               |

Метаданные: `source`, `filepath`, `filename`, `category`, `chunk_id`

### Структура

```
architecture-pro-quantumforge-software/
├── vector_index/
│   ├── build_index.py          # Скрипт построения индекса
│   ├── search_index.py         # Скрипт тестирования поиска
│   ├── README.md               # Этот файл
│   └── indices/
│       └── faiss_index/
│           ├── index.faiss     # Векторный индекс (~15 MB)
│           └── index.pkl       # Метаданные чанков
├── knowledge_base/
│   └── final/                  # База знаний (40 .txt файлов)
│       ├── characters/
│       ├── planets/
│       ├── events/
│       ├── organizations/
│       └── technologies/
└── requirements.txt            # Зависимости Python
```

### Использование индекса

```python
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-m3",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True, "batch_size": 16}
)

vectorstore = FAISS.load_local(
    "./indices/faiss_index",
    embeddings,
    allow_dangerous_deserialization=True
)

results = vectorstore.similarity_search_with_score("Кто такой Ivan Nebov?", k=3)
# L2 Distance: меньше = лучше
```


### Результаты тестов

| Запрос                                   | Top-1 источник                  | L2 Distance |
|------------------------------------------|---------------------------------|-------------|
| Кто такой Ivan Nebov?                    | `characters/luke_skywalker.txt` | 0.8687      |
| Что такое Svetomech?                     | `characters/obi_wan_kenobi.txt` | 1.0722      |
| Где находится Sukhostep?                 | `planets/tatooine.txt`          | 0.8313      |
| Что такое Orden Vedunov?                 | `organizations/jedi_order.txt`  | 0.8906      |
| Что произошло в Bitve pri Zelyonoy Lune? | `events/battle_of_yavin.txt`    | 0.7272      |
