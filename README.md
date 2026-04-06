# FastAPI Template

Production-ready шаблон FastAPI микросервиса с Clean Architecture, async поддержкой и современным инструментарием.

## Что это

Шаблон для быстрого создания новых FastAPI микросервисов. Включает предустановленную архитектуру, инфраструктуру (БД, кеш, NATS, логирование) и best practices. Готов к использованию как основа для новых сервисов.

## Для чего

- **Быстрый старт** — создание нового сервиса за минуты
- **Единообразие** — все сервисы следуют одной архитектуре
- **Production-ready** — DI, логирование, мониторинг, тесты из коробки
- **Масштабируемость** — Clean Architecture для легкого расширения

## Архитектура

**Clean Architecture** с четким разделением слоев:

```
app/
├── domain/          # Бизнес-логика, модели, интерфейсы (независимый слой)
├── application/     # Use cases и сервисы приложения
├── infrastructure/  # Реализации (БД, кеш, NATS, внешние API)
└── interfaces/      # API endpoints (FastAPI routes)
```

**Принципы:**
- Domain не зависит от других слоев
- Application зависит только от Domain
- Infrastructure реализует интерфейсы из Domain
- Interfaces зависит от всех слоев

## Технологический стек

- **FastAPI** — веб-фреймворк
- **SQLAlchemy 2.0+ (async)** — ORM для PostgreSQL
- **PostgreSQL** — основная БД
- **Redis** — кеширование
- **NATS JetStream** — межсервисное взаимодействие (pub/sub)
- **APScheduler** — планировщик задач
- **Dependency Injection** — `dependency-injector`
- **Python 3.14+** — современные возможности языка

## Быстрый старт

### Требования

- Python 3.14+
- [uv](https://github.com/astral-sh/uv)
- Docker & docker-compose

### Установка

```bash
# Клонировать и перейти в директорию
git clone <repository-url>
cd fastapi_template

# Установить зависимости
uv sync

# Запустить все сервисы
make up
```

Сервис доступен на `http://localhost:8001`

## Структура проекта

```
fastapi_template/
├── app/
│   ├── domain/              # Доменный слой
│   │   ├── models/          # Pydantic модели
│   │   ├── interfaces/      # Абстрактные интерфейсы
│   │   └── exceptions.py    # Доменные исключения
│   ├── application/         # Слой приложения
│   │   └── services/       # Бизнес-логика
│   ├── infrastructure/      # Инфраструктурный слой
│   │   ├── persistence/     # SQLAlchemy, репозитории
│   │   ├── cache/          # Redis клиент
│   │   └── messaging/      # NATS consumer/publisher
│   ├── interfaces/          # Слой представления
│   │   └── api/            # FastAPI routes, schemas
│   └── core/               # Ядро приложения
│       ├── config/         # Настройки (Pydantic Settings)
│       ├── di/             # Dependency Injection
│       └── logging.py     # Логирование
├── migrations/             # Alembic миграции
├── tests/                  # Тесты
├── docker-compose.yml      # Локальная разработка
└── Makefile               # Автоматизация задач
```

## Основные возможности

### NATS Messaging
- **Consumer**: batch processing, параллельная обработка, graceful shutdown
- **Publisher**: автоматическое создание stream, retry, переподключение

### Database
- Async SQLAlchemy 2.0+, Alembic миграции, Repository pattern

### Caching
- Redis с async поддержкой, интерфейс для замены реализации

### Task Scheduling
- APScheduler с поддержкой распределенной координации (Redis/PostgreSQL locks)

## Конфигурация

Настройки через переменные окружения с префиксами:
- `APP_*`, `DB_*`, `REDIS_*`, `NATS_*`, `SENTRY_*`, `CORS_*`

См. `.env.example` для полного списка.

## Разработка

```bash
# Форматирование кода
make format

# Проверка типов
make type-check

# Линтинг
make lint

# Тесты
make test

# Запуск локально
make up          # Запустить все сервисы
make down        # Остановить
make logs        # Логи
```

## API Endpoints

- `GET /api/v1/health` — health check
- `POST /api/v1/service/request` — пример обработки запроса
- `POST /api/v1/nats/publish` — тестовый эндпоинт для NATS

## Тестирование

- Unit тесты: `pytest tests/`
- Coverage: `make test` (результаты в `htmlcov/`)
- NATS тесты: `tests/test_nats_consumer.py`, `tests/test_nats_publisher.py`

## Документация

- API документация: `http://localhost:8001/docs` (Swagger)
- Альтернативная: `http://localhost:8001/redoc`
- Метрики: `http://localhost:8001/metrics` (Prometheus)

## Создание нового сервиса на основе шаблона

### Шаг 1: Копирование шаблона

```bash
# Из корня проекта
cp -r fastapi_template be/services/new-service-name
cd be/services/new-service-name
```

### Шаг 2: Обновление конфигурации проекта

**Обновить `pyproject.toml`:**
```toml
[project]
name = "new-service-name"
description = "Описание вашего сервиса"
```

**Обновить `docker-compose.yml`:**
- Изменить имена сервисов (например, `template_app` → `new_service_app`)
- Обновить порты при необходимости
- Обновить имена сетей и volumes

### Шаг 3: Замена примеров кода

**Application services:**
- Заменить `app/application/services/service.py` на свою бизнес-логику
- Обновить интерфейсы в `app/domain/interfaces/services/`

**API routes:**
- Заменить примеры в `app/interfaces/api/routes/service.py`
- Обновить или удалить `app/interfaces/api/routes/nats.py` (тестовый эндпоинт)
- Обновить роутер в `app/interfaces/api/routes/router.py`

**Domain models:**
- Заменить `app/domain/models/request.py` на свои модели
- Обновить репозитории в `app/infrastructure/persistence/`

### Шаг 4: Настройка миграций

```bash
# Удалить существующие миграции
rm -rf migrations/versions/*

# Создать первую миграцию для вашей схемы
make migrations-create MSG="initial schema"
```

**Обновить SQLAlchemy модели:**
- Заменить `app/infrastructure/persistence/models/request.py`
- Обновить репозитории под новые модели

### Шаг 5: Настройка NATS

**Обновить настройки в `app/core/config/nats.py`:**
```python
subject: str = "your-service.>"  # Ваш subject pattern
stream_name: str = "your-service"  # Имя stream
consumer_durable: str = "your-service-consumer"  # Имя consumer
```

**Заменить message handler:**
- Создать свой handler в `app/infrastructure/messaging/message_handler.py`
- Или создать новый класс, реализующий `IMessageHandler`
- Обновить DI контейнер в `app/core/di/containers.py`

**Обновить wiring в DI:**
- Добавить новые модули в `wiring_config` в `containers.py`

### Шаг 6: Очистка и проверка

```bash
# Удалить тестовые файлы (если не нужны)
rm -rf tests/test_nats_*.py  # или обновить под свои тесты

# Обновить зависимости
make deps-update

# Проверить код
make validate
make test
```

### Шаг 7: Обновление документации

- Обновить `README.md` с описанием вашего сервиса
- Обновить `.env.example` с нужными переменными

## Лицензия

[Указать лицензию]