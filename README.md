# docsAI

**Семейный архив документов с Verified Agentic RAG** — медицина, ЖКХ, кредиты,
недвижимость и домашние документы (гарантии, инструкции). Документы хранятся в
оригинале, автоматически категоризируются и раскладываются по членам семьи; вопросы
к архиву проходят через Verifier-агента и возвращаются с источниками и confidence score.

**Возможности:**
- 📷 **Фото — основной способ загрузки**: сфотографируйте бумажный документ
  (несколько фото = страницы одного документа), Claude Vision дословно распознает
  текст, таблицы и рукописные фрагменты; нечитаемые места помечаются
  `[неразборчиво]` с предупреждением. HEIC с iPhone поддерживается,
  фото автоматически поворачиваются по EXIF и сжимаются
- 📁 Библиотека документов: загрузка, просмотр содержимого, фото страниц
  и извлечённых данных, скачивание оригиналов, удаление; фильтры по категории
  и поиск по названию
- 👨‍👩‍👧 Члены семьи: документы привязываются к конкретному человеку
- 🩺 Медицинские данные: врачи, диагнозы, лекарства, клиники извлекаются автоматически
- ⏰ Напоминания: предстоящие платежи (кредиты, ЖКХ, приёмы) на ближайшие 30 дней
- 💬 Чат с проверенными ответами (Web UI + Telegram)

## Архитектура

```
Пользовательский запрос
        ↓
[Web UI (React)  /  Telegram Bot]
        ↓
FastAPI  →  LangGraph Orchestrator
              ├── Planner Agent        (claude-sonnet-5)   — декомпозиция запроса
              ├── Hybrid Retriever     pgvector + FTS('russian') + metadata + Voyage rerank-2
              ├── Structured Query     точные суммы/даты из Postgres (не через LLM)
              ├── Calculator           детерминированная арифметика в Python
              ├── Reasoner Agent       (claude-opus-4-8)   — черновик только из evidence
              └── Verifier Agent       (claude-opus-4-8)   — проверка каждого факта,
                                        при низкой уверенности → повторный поиск
        ↓
Ответ + Источники (документ/раздел) + Confidence 0–100 + Warnings
```

**Слои:**

| Слой | Реализация |
|---|---|
| Ingestion | **Фото → Claude Vision (claude-opus-4-8)** — дословная транскрипция в Markdown с сохранением таблиц; электронные файлы → Docling/LlamaParse; извлечение сущностей и платежей (claude-haiku-4-5), включая медицинские (врач/диагноз/лекарство/клиника); автокатегоризация: кредит / ЖКХ / мед / собственность |
| Library | Оригиналы файлов на диске (volume `uploads`), метаданные и извлечённые данные в Postgres; CRUD по документам и членам семьи; напоминания по платежам |
| Storage | PostgreSQL (+pgvector для эмбеддингов, JSONB для аудита) + Neo4j (связи документы↔сущности) |
| Retrieval | Гибридный поиск: семантика (voyage-3) + keyword (Postgres FTS, russian) + фильтры метаданных; реранкинг Voyage rerank-2 |
| Agents | LangGraph-граф с циклом верификации (см. `backend/app/agents/graph.py`) |
| Output & Safety | Всегда источники + confidence; при низкой уверенности — предупреждение; каждый шаг агентов пишется в таблицу `agent_runs` (аудит) |

## Быстрый старт

```bash
cp .env.example .env        # заполнить ANTHROPIC_API_KEY и VOYAGE_API_KEY
make up                     # Postgres+pgvector, Neo4j, backend, frontend, bot
make seed                   # загрузить пример кредитной справки из data/samples/
```

- Web UI: http://localhost:5173
- API docs: http://localhost:8000/docs
- Neo4j browser: http://localhost:7474

Проверочный вопрос: **«Сколько у нас всего долгов по кредитам на июль 2026?»** —
ответ должен ссылаться на справку № КД-2024-11-458 с суммой 4 822 560,55 руб.

### Telegram-бот

Задайте `TELEGRAM_BOT_TOKEN` в `.env` (получить у @BotFather) и перезапустите
`docker compose up -d bot`. Без токена сервис бота просто завершается.

Бот понимает:
- **фото** — одиночное фото или альбом (альбом = страницы одного документа);
- **файлы** — pdf/txt/md как вложение;
- **текст** — вопрос к архиву, ответ придёт с источниками и confidence.

## Локальная разработка (без Docker)

```bash
# Backend
cd backend
pip install -e ".[dev]"        # + ".[parsing]" для PDF через Docling
docker compose up -d db neo4j
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (проксирует /api на :8000)
cd frontend
npm install
npm run dev
```

## Тесты и линтеры

```bash
make test    # pytest — LLM и эмбеддинги замоканы, работает офлайн без ключей
make lint    # ruff + eslint
```

## Конфигурация

Все настройки — через переменные окружения (`.env.example`):
модели на каждого агента (`REASONER_MODEL`, `VERIFIER_MODEL`, `PLANNER_MODEL`,
`EXTRACTION_MODEL`), эмбеддинги, подключения к БД, порог `MIN_CONFIDENCE`,
при котором Verifier отправляет пайплайн на повторный поиск.

## Структура репозитория

```
backend/
  app/
    api/routes/      # /api/health, /api/documents (CRUD+file), /api/query,
                     # /api/family, /api/reminders
    ingestion/       # parser (Docling), chunker, entities, categorizer
    storage/         # SQLAlchemy-модели, pgvector/FTS поиск, Neo4j
    retrieval/       # hybrid search + reranker
    agents/          # LangGraph: state, planner, retriever, structured_query,
                     #            calculator, reasoner, verifier, graph
    llm/             # обёртки Anthropic SDK и Voyage AI
  migrations/        # Alembic
  tests/             # офлайн-тесты (FakeLLM)
frontend/            # React + Vite + TS: чат, загрузка, источники, confidence
bot/                 # python-telegram-bot → POST /api/query
data/samples/        # пример кредитной справки для демо
```

## Что дальше (заготовки с TODO)

- LlamaParse-интеграция для сложных таблиц (`ingestion/parser.py`)
- Синтез SQL для произвольных структурных запросов (`agents/structured_query.py`)
- Песочница code-executor для Calculator (`agents/calculator.py`)
- Графовые запросы Neo4j «кредит → дом → платежи» (`storage/graph.py`)
- LLM-реранкинг как fallback (`retrieval/reranker.py`)
- Стриминг ответов, аутентификация, локальная fallback-модель
