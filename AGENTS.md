# FastAPI Template — AGENTS.md

Ты находишься в **эталонном шаблоне** FastAPI-сервиса.

> **Главный источник архитектурных правил:** [`agents/backend.md`](../agents/backend.md)
> Прочитай его до начала работы с кодом.

---

## Что такое этот шаблон

`fastapi_template/` — готовая точка старта для нового микросервиса.
Уже реализованы:
- Clean Architecture (domain / application / infrastructure / interfaces / core)
- DI через `dependency-injector` (`app/core/di/containers.py`)
- Async SQLAlchemy + Alembic (`migrations/`)
- Redis / NATS клиенты с интерфейсами
- JWT-аутентификация (`app/core/auth/`)
- Prometheus-инструментация + Sentry + aiologger
- Пример сущности `Request` (для удаления или переименования)

---

## Как создать новый сервис

1. Скопировать шаблон: `cp -r fastapi_template services/my-service`
2. Обновить `pyproject.toml`: поля `name`, `description`
3. Обновить `docker-compose.yml`: имена сервисов, порты
4. Удалить или переименовать пример сущности `Request`
5. Добавить свои модели, команды, сервисы по конвенциям из `agents/backend.md` секция 3
6. Обновить `NATS_SUBJECT`, `NATS_STREAM_NAME` в конфиге
7. Пересоздать миграции: `rm migrations/versions/* && make migrations-create MSG="init"`
8. Зарегистрировать exception handlers для новых исключений в `app/core/exception_handlers.py`

---

## Команды

```bash
make up            # Docker: поднять сервис
make test          # Тесты с coverage
make validate      # format + lint + type-check
make migrations-create MSG="..."
make migrations-up
```

---

## Структура шаблона

```
fastapi_template/
├── app/
│   ├── domain/           # Бизнес-правила (модели, исключения, интерфейсы)
│   ├── application/      # Use cases (команды, сервисы)
│   ├── infrastructure/   # Адаптеры (БД, Redis, NATS)
│   ├── interfaces/       # FastAPI routes + схемы
│   └── core/             # DI, конфиг, логирование, auth
├── migrations/           # Alembic
├── tests/
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
└── Makefile
```
