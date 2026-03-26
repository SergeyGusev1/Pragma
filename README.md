# Pragma — Task Manager API

Бэкенд-приложение для управления проектами и задачами с Telegram-уведомлениями и фоновыми напоминаниями о дедлайнах.

Реализован на **FastAPI**, **PostgreSQL**, **Redis**, **Celery** и **aiogram**.

---

## Стек технологий

| Слой | Технология |
|---|---|
| API | FastAPI 0.115 + Uvicorn |
| База данных | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Миграции | Alembic |
| Кэш / Брокер | Redis 7 |
| Фоновые задачи | Celery 5 (worker + beat) |
| Telegram-бот | aiogram 3.18 |
| Аутентификация | JWT (access + refresh токены) |
| Валидация | Pydantic v2 |
| Контейнеризация | Docker + Docker Compose |

---

## Структура проекта

```
pet_project/
├── app/                        # FastAPI-приложение
│   ├── api/v1/                 # REST-эндпоинты
│   │   ├── auth.py             # Регистрация, вход, обновление токена
│   │   ├── users.py            # Профиль пользователя
│   │   ├── projects.py         # Проекты и участники
│   │   └── tasks.py            # Задачи и теги
│   ├── models/                 # SQLAlchemy ORM-модели
│   ├── schemas/                # Pydantic-схемы запросов/ответов
│   ├── services/               # Бизнес-логика
│   ├── repositories/           # Слой доступа к базе данных
│   └── core/                   # Конфиг, БД, безопасность, Redis
├── bot/                        # Telegram-бот (aiogram)
│   └── handlers/notifications.py
├── tasks/                      # Celery-задачи
│   ├── celery_app.py
│   └── reminder_tasks.py       # Напоминания о дедлайнах
├── alembic/                    # Миграции базы данных
└── tests/
    ├── unit/
    └── integration/
```

---

## API

### Аутентификация
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/v1/auth/register` | Регистрация нового пользователя |
| `POST` | `/api/v1/auth/login` | Вход, получение access + refresh токенов |
| `POST` | `/api/v1/auth/refresh` | Обновление access-токена |
| `POST` | `/api/v1/auth/logout` | Выход, инвалидация токена |

### Проекты
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/v1/projects` | Создать проект |
| `GET` | `/api/v1/projects` | Список проектов пользователя |
| `GET` | `/api/v1/projects/{id}` | Детали проекта |
| `PATCH` | `/api/v1/projects/{id}` | Обновить проект |
| `DELETE` | `/api/v1/projects/{id}` | Удалить проект |
| `POST` | `/api/v1/projects/{id}/members` | Добавить участника |
| `PATCH` | `/api/v1/projects/{id}/members/{user_id}` | Изменить роль участника |
| `DELETE` | `/api/v1/projects/{id}/members/{user_id}` | Удалить участника |

### Задачи
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `POST` | `/api/v1/projects/{id}/tasks` | Создать задачу |
| `GET` | `/api/v1/projects/{id}/tasks` | Список задач (с фильтрами) |
| `GET` | `/api/v1/projects/{id}/tasks/{task_id}` | Получить задачу |
| `PATCH` | `/api/v1/projects/{id}/tasks/{task_id}` | Обновить задачу |
| `DELETE` | `/api/v1/projects/{id}/tasks/{task_id}` | Удалить задачу |

**Фильтры задач:** `status`, `priority`, `assignee_id`, `deadline_before`, `deadline_after`, `page`, `size`

### Теги
| Метод | Эндпоинт | Описание |
|-------|----------|----------|
| `GET` | `/api/v1/tags` | Список всех тегов |
| `POST` | `/api/v1/tags` | Создать тег |
| `POST` | `/api/v1/projects/{id}/tasks/{task_id}/tags/{tag_id}` | Прикрепить тег к задаче |
| `DELETE` | `/api/v1/projects/{id}/tasks/{task_id}/tags/{tag_id}` | Открепить тег |

---

## Быстрый старт

### Требования

- [Docker](https://www.docker.com/) и Docker Compose

### 1. Клонировать репозиторий

```bash
git clone https://github.com/SergeyGusev1/Pragma.git
cd Pragma
```

### 2. Настроить окружение

```bash
cp .env.example .env
```

Заполнить `.env`:

```env
SECRET_KEY=your-super-secret-key-change-in-production
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

POSTGRES_DB=taskmanager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 3. Запустить

```bash
docker compose up --build
```

Запустятся следующие сервисы:

| Сервис | Описание | Порт |
|--------|----------|------|
| `api` | FastAPI-приложение | `8001` |
| `db` | PostgreSQL | `5433` |
| `redis` | Redis | `6379` |
| `celery_worker` | Воркер фоновых задач | — |
| `celery_beat` | Планировщик задач | — |
| `telegram_bot` | Telegram-бот | — |
| `migrations` | Alembic-миграции при старте | — |

---

## Документация API

После запуска доступна интерактивная документация:

- **Swagger UI** → http://localhost:8001/docs
- **ReDoc** → http://localhost:8001/redoc
- **Health check** → http://localhost:8001/health

---

## Запуск тестов

```bash
# Установить dev-зависимости
pip install -r requirements-dev.txt

# Запустить все тесты
pytest

# С отчётом о покрытии
pytest --cov=app tests/
```

---

## Архитектура

Приложение построено по принципу **монолита с процессной декомпозицией** — единая кодовая база и Docker-образ, но разные контейнеры запускают разные точки входа:

```
┌─────────────────────────────────────────────┐
│             Единая кодовая база              │
│                                              │
│  ┌──────────┐  ┌────────┐  ┌─────────────┐  │
│  │ FastAPI  │  │ Celery │  │ Telegram Bot│  │
│  │   API    │  │ Worker │  │  (aiogram)  │  │
│  └────┬─────┘  └───┬────┘  └──────┬──────┘  │
└───────┼────────────┼──────────────┼──────────┘
        │            │              │
   ┌────▼────┐   ┌───▼───┐         │
   │Postgres │   │ Redis │◄─────────┘
   └─────────┘   └───────┘
```

---

## Лицензия

MIT
