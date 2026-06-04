# HR ETL – загрузка кадровых данных из Excel в PostgreSQL

Production-ready ETL для загрузки сотрудников, должностей, дат приёма и аттестаций из Excel-файла.

## Особенности

- Идемпотентность (upsert по табельному номеру)
- Staging-слой для аудита
- Reject-логирование (бракованные строки)
- Потоковый хеш файла (экономия памяти)
- Batch-вставка (execute_values, page_size=1000)
- Fuzzy-маппинг колонок (rapidfuzz, порог 85%)
- Advisory lock для предотвращения параллельных запусков
- Автоматический аудит каждого запуска

## Требования

- Python 3.11+
- Docker и Docker Compose
- Git

## Запуск с GitHub

### 1. Клонировать репозиторий

```bash
git clone https://github.com/YOUR_USERNAME/hr-etl-project.git
cd hr-etl-project
```

Замените `YOUR_USERNAME/hr-etl-project` на URL вашего репозитория.

### 2. Настроить окружение

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Подготовить данные

Положите Excel-файл с кадровыми данными в папку `data/`:

```text
data/ш.xls
```

Имя файла задаётся в `.env` (`HR_EXCEL_FILENAME=ш.xls`).

### 4. Запустить PostgreSQL

```bash
make up
```

При первом запуске автоматически применяются SQL-схемы из папки `sql/`.
База доступна на порту **55432** (см. `.env`).

### 5. Загрузить данные (ETL)

```bash
make hr-etl
```

Повторный запуск того же файла будет пропущен (идемпотентность по хешу).

### 6. Запустить дашборд

```bash
make dash
```

Откройте в браузере: [http://127.0.0.1:8050](http://127.0.0.1:8050)

## Быстрый старт (локально, без clone)

1. Скопируйте `.env.example` в `.env`
2. Положите файл `ш.xls` в папку `data/`
3. Запустите PostgreSQL: `make up`
4. SQL-схемы применяются автоматически при первом старте
5. Запустите ETL: `make hr-etl`
6. Запустите дашборд: `make dash`

## Полезные команды

| Команда | Описание |
|---|---|
| `make up` | Запустить PostgreSQL |
| `make down` | Остановить контейнеры |
| `make reset-db` | Остановить и удалить volume БД |
| `make hr-etl` | Загрузить Excel в PostgreSQL |
| `make dash` | Запустить HR-дашборд |
| `make test` | Запустить тесты |
| `make install-dev` | Установить зависимости для тестов |

## Проверка результатов

```bash
docker exec -it hr_postgres psql -U hr_user -d hr_db -c "SELECT COUNT(*) FROM core.hr_employee;"
```

## Проверка результатов

```bash
docker exec -it hr_postgres psql -U hr_user -d hr_db -c "SELECT * FROM core.hr_employee LIMIT 10;"
```

## Запуск тестов

```bash
make install-dev
make test
```

Требуется Docker (testcontainers поднимает временный PostgreSQL).

## Dashboard

После загрузки данных запустите Dash-дашборд:

```bash
make dash
```

Откройте в браузере: [http://127.0.0.1:8050](http://127.0.0.1:8050)

На дашборде доступны 4 вкладки:

1. **Обзор** — KPI, отделы, пол, приёмы, состояние, таблица сотрудников
2. **Структура** — отделы, должности, heatmap отдел×пол, средний стаж
3. **Охрана труда** — вредники, допуски, статус аттестаций, таблица рисков
4. **Качество данных** — заполненность полей, reject-ы, история ETL

Глобальные фильтры: отдел, пол, вредники, состояние, год приёма, поиск.
