# TimeWarden — Task Manager API

A backend application for managing projects and tasks, with Telegram notifications and background reminders.

Built with **FastAPI**, **PostgreSQL**, **Redis**, **Celery**, and **aiogram**.

---

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115 + Uvicorn |
| Database | PostgreSQL 16 + SQLAlchemy 2 (async) |
| Migrations | Alembic |
| Cache / Broker | Redis 7 |
| Background tasks | Celery 5 (worker + beat) |
| Telegram bot | aiogram 3.18 |
| Auth | JWT (access + refresh tokens) |
| Validation | Pydantic v2 |
| Containerization | Docker + Docker Compose |

---

## Project Structure

```
pet_project/
├── app/                        # FastAPI application
│   ├── api/v1/                 # REST endpoints
│   │   ├── auth.py             # Registration, login, token refresh
│   │   ├── users.py            # User profile
│   │   ├── projects.py         # Projects & members
│   │   └── tasks.py            # Tasks & tags
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Business logic layer
│   ├── repositories/           # Database access layer
│   └── core/                   # Config, DB, security, Redis
├── bot/                        # Telegram bot (aiogram)
│   └── handlers/notifications.py
├── tasks/                      # Celery tasks
│   ├── celery_app.py
│   └── reminder_tasks.py       # Deadline reminders
├── alembic/                    # Database migrations
└── tests/
    ├── unit/
    └── integration/
```

---

## API Overview

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/auth/register` | Register a new user |
| `POST` | `/api/v1/auth/login` | Login, get access + refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Refresh access token |

### Projects
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects` | Create project |
| `GET` | `/api/v1/projects` | List user's projects |
| `GET` | `/api/v1/projects/{id}` | Get project details |
| `PATCH` | `/api/v1/projects/{id}` | Update project |
| `DELETE` | `/api/v1/projects/{id}` | Delete project |
| `POST` | `/api/v1/projects/{id}/members` | Add member |

### Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/projects/{id}/tasks` | Create task |
| `GET` | `/api/v1/projects/{id}/tasks` | List tasks (with filters) |
| `GET` | `/api/v1/projects/{id}/tasks/{task_id}` | Get task |
| `PATCH` | `/api/v1/projects/{id}/tasks/{task_id}` | Update task |
| `DELETE` | `/api/v1/projects/{id}/tasks/{task_id}` | Delete task |

**Task filters:** `status`, `priority`, `assignee_id`, `deadline_before`, `deadline_after`, `page`, `size`

### Tags
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/v1/tags` | List all tags |
| `POST` | `/api/v1/tags` | Create tag |
| `POST` | `/api/v1/projects/{id}/tasks/{task_id}/tags/{tag_id}` | Attach tag to task |
| `DELETE` | `/api/v1/projects/{id}/tasks/{task_id}/tags/{tag_id}` | Remove tag from task |

---

## Getting Started

### Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose

### 1. Clone the repository

```bash
git clone https://github.com/your-username/timewarden.git
cd timewarden
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your values:

```env
SECRET_KEY=your-super-secret-key-change-in-production
TELEGRAM_BOT_TOKEN=your-telegram-bot-token

POSTGRES_DB=taskmanager
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### 3. Run

```bash
docker compose up --build
```

The following services will start:

| Service | Description | Port |
|---------|-------------|------|
| `api` | FastAPI application | `8001` |
| `db` | PostgreSQL | `5433` |
| `redis` | Redis | `6379` |
| `celery_worker` | Background task worker | — |
| `celery_beat` | Task scheduler | — |
| `telegram_bot` | Telegram bot | — |
| `migrations` | Runs Alembic migrations on startup | — |

---

## API Docs

Once running, interactive documentation is available at:

- **Swagger UI** → http://localhost:8001/docs
- **ReDoc** → http://localhost:8001/redoc
- **Health check** → http://localhost:8001/health

---

## Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# With coverage
pytest --cov=app tests/
```

---

## Architecture

The application is a **monolith with process decomposition** — a single codebase and Docker image, with different containers running different entry points:

```
┌─────────────────────────────────────────────┐
│                Single Codebase               │
│                                              │
│  ┌──────────┐  ┌────────┐  ┌─────────────┐  │
│  │ FastAPI  │  │ Celery │  │ Telegram Bot│  │
│  │   API    │  │Worker  │  │  (aiogram)  │  │
│  └────┬─────┘  └───┬────┘  └──────┬──────┘  │
└───────┼────────────┼──────────────┼──────────┘
        │            │              │
   ┌────▼────┐   ┌───▼───┐         │
   │Postgres │   │ Redis │◄─────────┘
   └─────────┘   └───────┘
```

---

## License

MIT
