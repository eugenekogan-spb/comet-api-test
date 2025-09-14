# ТЗ: Приложение для сравнения LLM (LLM Runner)

## 1. Цель и задачи
**Цель:** дать пользователю удобный инструмент для массового запуска промптов на разных LLM‑провайдерах (OpenAI‑совместимые и иные), фиксировать параметры, ответы, метрики (токены/латентность/стоимость) и быстро разметить качество (рейтинг, теги, заметки), включая A/B сравнение.

**Ключевые задачи:**
- Хранение датасета задач: шаблоны промптов (версии), входные тексты/переменные.
- Запуск батчей на нескольких моделях/провайдерах с параметрами (temperature/top_p/max_tokens/seed/stop и др.).
- Сбор результатов: полный сырой ответ, тайминги, токены, стоимость.
- Ручная оценка (Likert 1–5), теги, заметки; парные сравнения A/B.
- Отчёты/дашборды: средний рейтинг по модели, винрейт, цена/1000 задач, распределение латентности.
- Импорт/экспорт датасета и результатов (CSV/JSONL), воспроизводимость (context hash).

## 2. Технологии и окружение
- **Язык:** Python 3.11+
- **GUI:** Streamlit
- **БД:** SQLite (через SQLAlchemy)
- **HTTP:** httpx
- **Совместимые SDK:** OpenAI‑совместимый клиент (через OpenAI SDK или собственный HTTP слой), адаптеры под провайдеров.
- **Секреты:** `.env` (python‑dotenv)
- **Линт/формат:** ruff + black, mypy (опц.)
- **Логи:** loguru

## 3. Структура проекта
```
llm_runner/
  app.py                      # Streamlit entrypoint
  core/
    providers/
      base.py                 # интерфейс провайдера
      openai_like.py          # OpenAI-compatible (в т.ч. Comet via base_url)
      anthropic.py            # пример «несовместимого» (через HTTP адаптер)
    runner.py                 # батч-запуски, ретраи, rate limit
    hashing.py                # context_hash
    cost.py                   # оценка стоимости
  data/
    importers.py              # CSV/JSONL -> tasks
    exporters.py              # выгрузки
  db/
    models.py                 # SQLAlchemy ORM
    schema.sql                # чистое SQL для init
    repo.py                   # CRUD слой
    migrations/               # alembic (опц.)
  ui/
    pages/
      01_dataset.py
      02_runs.py
      03_evaluate.py
      04_compare_ab.py
      05_reports.py
      06_settings.py
    widgets.py
  utils/
    timing.py, json.py
  tests/
    test_repo.py, test_runner.py, test_ui_smoke.py
.env.example
requirements.txt
README.md
```

## 4. Модель данных (SQLite)
```sql
-- Задания/кейсы
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,                -- UUID4
  template_version TEXT NOT NULL,
  prompt_template TEXT NOT NULL,      -- может содержать плэйсхолдеры {var}
  input_text TEXT,                    -- необязательный сырой текст
  vars_json TEXT,                     -- JSON с переменными темплейта
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Запуски (конкретные прогоны задачи на модели)
CREATE TABLE IF NOT EXISTS runs (
  id TEXT PRIMARY KEY,                -- UUID4
  task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  provider TEXT NOT NULL,             -- 'openai', 'comet', 'anthropic', ...
  base_url TEXT,                      -- для OpenAI-like
  model TEXT NOT NULL,
  params_json TEXT NOT NULL,          -- temperature, top_p, max_tokens, stop, seed...
  messages_json TEXT NOT NULL,        -- system/user/messages в полном виде
  context_hash TEXT NOT NULL,
  started_at TEXT,
  ended_at TEXT,
  latency_ms INTEGER,
  prompt_tokens INTEGER,
  completion_tokens INTEGER,
  total_tokens INTEGER,
  cost_usd REAL,
  finish_reason TEXT,
  response_json TEXT NOT NULL         -- полный сырой ответ API
);

-- Оценки качества
CREATE TABLE IF NOT EXISTS evaluations (
  id TEXT PRIMARY KEY,                -- UUID4
  run_id TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  rating INTEGER CHECK (rating BETWEEN 1 AND 5),
  label_tags TEXT,                    -- JSON array строк
  notes TEXT,
  created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Парные сравнения (A/B)
CREATE TABLE IF NOT EXISTS pairwise (
  id TEXT PRIMARY KEY,
  run_a TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  run_b TEXT NOT NULL REFERENCES runs(id) ON DELETE CASCADE,
  winner_run TEXT NOT NULL            -- run_a | run_b | 'draw'
);

-- Индексы
CREATE INDEX IF NOT EXISTS idx_runs_task ON runs(task_id);
CREATE INDEX IF NOT EXISTS idx_eval_run ON evaluations(run_id);
```

## 5. Логика и требования
### 5.1 Провайдеры
- **Интерфейс** (`Provider`):
  - `generate(messages: list[dict], model: str, params: dict) -> ProviderResult`
  - Возвращает: текст (или части), usage (tokens), finish_reason, сырой JSON, тайминги.
- **OpenAI‑совместимый**: один класс `OpenAILikeProvider` с параметрами `api_key`, `base_url`.
  - Для Comet указывать `base_url=https://api.comet.com` (можно переопределять в настройках UI).
- **Ретраи и лимиты**: экспоненциальный backoff (джиттер), обработка 429/5xx.
- **Семплирование**: поддержать `n` сэмплов (опц.), сохранение отдельных `run` на каждый сэмпл.

### 5.2 Формирование сообщений
- Системный промпт из `prompt_template` + подстановка `{vars}`.
- Пользовательское сообщение: `input_text` или собранное из формы.
- В `messages_json` хранить весь массив сообщений и финальные `params` (для воспроизводимости).

### 5.3 Context Hash
- `SHA256` от: `provider|base_url|model|sorted(params)|messages_json|template_version`.
- Используется для дедупликации и трекинга изменений.

### 5.4 Стоимость
- Маппинг стоимости по моделям (конфиг в JSON). При отсутствии — `NULL`.
- Поддержать ручную переоценку коэффициентов в Settings.

### 5.5 Импорт/экспорт
- Импорт датасета: CSV или JSONL (`task_id`, `template_version`, `prompt_template`, `input_text`, `vars_json`).
- Экспорт: результаты (`runs` + `evaluations`) в JSONL/CSV; отчёты в CSV.

### 5.6 Оценивание
- Легкая разметка: хоткеи `1..5` для рейтинга, быстрые теги (чипсы), поле заметки.
- A/B режим: два ответа бок‑о‑бок, выбор победителя (`A`, `B`, `=`, хоткеи `Q/W/E`).

### 5.7 Отчёты
- Таблица моделей: `avg_rating`, `winrate`, `cost_per_1k_tasks`, `avg_latency`, `avg_tokens`.
- Графики: распределение рейтингов, latency histogram, цена vs. качество (scatter).

### 5.8 Безопасность и приватность
- Хранить ключи только в локальном `.env` и в сессии Streamlit (не в БД).
- Маскирование ключей в UI, не логировать payload с PII по умолчанию.

### 5.9 Тесты
- Unit для `context_hash`, репозитория, retry‑логики.
- Смоук‑тест UI (streamlit‑testing) и фикстуры с мок‑провайдером.

## 6. UI/UX (Streamlit)
### Страница 01 — Dataset
- Таблица задач (поиск/фильтры), кнопки: **Add**, **Import**, **Export**.
- Форма добавления/редактирования: `template_version`, `prompt_template` (многостр.), `input_text`, `vars_json` (валидатор JSON).
- Превью подстановки плэйсхолдеров.

### Страница 02 — Runs
- Выбор задач (мультиселект, фильтр по версии шаблона).
- Профиль запуска: провайдер, base_url, модель, параметры (`temperature`, `top_p`, `max_tokens`, `stop`, `seed`, `n`).
- Кнопка **Run batch** → прогресс‑индикатор; результаты ниже в таблице.
- Карточка результата: ответ, токены, latency, стоимость, **Save Evaluation**.

### Страница 03 — Evaluate
- Лента карточек `run` → быстрые рейтинги (1–5), теги (чипсы), заметки (autosave).
- Фильтры: по модели/версии/дате/рейтингу/тегам.

### Страница 04 — Compare A/B
- Выбор задачи → два `run` рядом, хоткеи `Q`=A, `W`=B, `E`=Draw.
- Запись в `pairwise`.

### Страница 05 — Reports
- KPI‑карточки (avg rating, winrate, cost/1000, latency) по модели.
- Графики (matplotlib/altair):
  - boxplot latency по моделям;
  - scatter cost vs rating;
  - histogram ratings;
  - bar tokens per model.
- Экспорт CSV.

### Страница 06 — Settings
- Ввод ключей: OpenAI, Comet (и др.).
- Base URL для OpenAI‑like провайдеров (например, `https://api.comet.com`).
- Стоимость моделей (редактируемая таблица).
- Тех.настройки: таймауты, ретраи, параллелизм (кол-во воркеров), дефолт‑параметры.

## 7. Нефункциональные требования
- Воспроизводимость: любой run можно повторить по `context_hash`.
- Надёжность: ретраи 3–5, таймауты сетевых вызовов, идемпотентность записи `runs`.
- Производительность: батчи с параллелизмом (asyncio/ThreadPool, лимит одновременных запросов).
- UX: все операции не блокируют UI; прогресс‑бар; подсветка новых результатов.

## 8. Интерфейсы и примеры кода
### 8.1 Базовый интерфейс провайдера
```python
# core/providers/base.py
from dataclasses import dataclass

@dataclass
class ProviderResult:
    text: str | None
    usage: dict
    finish_reason: str | None
    raw: dict
    latency_ms: int

class Provider:
    def generate(self, messages: list[dict], model: str, **params) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError
```

### 8.2 OpenAI‑like провайдер
```python
# core/providers/openai_like.py
import time, httpx, os
from .base import Provider, ProviderResult

class OpenAILikeProvider(Provider):
    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url or "https://api.openai.com/v1"

    def generate(self, messages, model, **params) -> ProviderResult:
        url = f"{self.base_url}/chat/completions"
        payload = {"model": model, "messages": messages} | params
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        t0 = time.perf_counter()
        with httpx.Client(timeout=60) as client:
            r = client.post(url, json=payload, headers=headers)
            r.raise_for_status()
            data = r.json()
        dt = int((time.perf_counter() - t0) * 1000)
        choice = data["choices"][0]
        text = choice.get("message", {}).get("content")
        usage = data.get("usage", {})
        return ProviderResult(text=text, usage=usage, finish_reason=choice.get("finish_reason"), raw=data, latency_ms=dt)
```

### 8.3 Батч‑раннер с ретраями
```python
# core/runner.py
import asyncio, random, time
from loguru import logger

async def run_with_retries(fn, *, retries=3, base=0.5, max_delay=8.0):
    for i in range(retries + 1):
        try:
            return await fn()
        except Exception as e:
            if i == retries:
                raise
            delay = min(max_delay, base * 2 ** i) * (0.5 + random.random())
            logger.warning(f"Retry {i+1}: {e} -> sleep {delay:.2f}s")
            await asyncio.sleep(delay)
```

## 9. Потоки и сценарии
1) **Создать датасет**: вручную или импорт CSV/JSONL → записи в `tasks`.
2) **Настроить провайдеры**: ввести ключи и `base_url` для Comet.
3) **Запустить батч**: выбрать задачи, модель/провайдера, параметры → `runs`.
4) **Разметить**: поставить оценки, теги, заметки; при необходимости провести A/B.
5) **Аналитика**: открыть Reports, посмотреть сравнительные метрики, экспортировать.

## 10. Acceptance Criteria
- Любой `run` воспроизводим (совпадает `context_hash`, параметры и сообщения сохранены).
- Можно импортировать ≥1000 задач и прогнать их по ≥3 моделям без падений.
- UI позволяет поставить рейтинг и теги минимум для 100 `run` подряд без перезагрузки.
- Reports показывают агрегаты и экспортируются в CSV.
- Поддержан OpenAI‑like провайдер с кастомным `base_url` (Comet).

## 11. Роадмап (опционально)
- Поддержка инструментов и функций (tool calling), JSON mode.
- Bradley–Terry/Elo агрегатор для парных сравнений.
- Автооценка на задачах с эталоном (string similarity / BLEU / ROUGE / factuality‑чеки).
- Мультисэмплы и rerank.
- Командная работа: многопользовательский режим (вне SQLite).

## 12. Настройки и переменные окружения
- `OPENAI_API_KEY` (опц.), `COMET_API_KEY` (опц.).
- `OPENAI_BASE_URL` (дефолт `https://api.openai.com/v1`), `COMET_BASE_URL` (напр., `https://api.comet.com`).
- `LLM_RUNNER_DB` путь к SQLite (по умолчанию `./llm_runner.db`).
- Параметры таймаутов/ретраев/параллелизма.

## 13. Установка и запуск
```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить ключи
streamlit run app.py
```

## 14. Риски и ограничения
- Ограничения провайдеров по rate limit; варьирующиеся версии моделей.
- Точность расчёта стоимости зависит от актуальности тарифов.
- Различия токенизаторов → несопоставимые usage между провайдерами.

## 15. Мини‑бэклог задач для Cursor
- Сгенерировать скелет файлов/папок.
- Реализовать `db/models.py` и `repo.py` + init БД из `schema.sql`.
- Написать `OpenAILikeProvider` + форму Settings.
- Страницы Dataset и Runs (минимальный флоу).
- Сохранение результатов `runs` и быстрые оценки в Evaluate.
- Первая версия Reports (таблица + 1–2 графика).
- Импорт/экспорт CSV/JSONL.

