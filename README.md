# RecruitFlow

RecruitFlow — CRM/ATS для небольшой рекрутинговой команды (3–10 человек). Помогает вести базу
кандидатов и вакансий, двигать кандидатов по воронке найма (канбан), ставить задачи и
напоминания, смотреть статистику и выгружать данные в CSV.

**Бэкенд готов и покрыт тестами** (26 pytest-тестов: аутентификация, кандидаты с
дедупликацией, вакансии, канбан-воронка с историей, комментарии/задачи, дашборд, CSV, GDPR).
**Фронтенд готов**: React + TypeScript + Mantine, страницы дашборда, кандидатов, карточки
кандидата, вакансий, канбан-доски с перетаскиванием и управления пользователями;
типизация `tsc` без ошибок, сборка `npm run build` проходит, 5 vitest-тестов.
Swagger-документация API доступна на `http://localhost:8000/api/docs` (только вне prod).

## Стек

- **Backend:** Python 3.12, FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 16, JWT, bcrypt.
- **Frontend:** React 18, TypeScript, Vite, Mantine 8 (nginx в прод-образе).
- **Инфраструктура:** Docker Compose; в продакшене — Caddy (HTTPS/Let's Encrypt) и nginx для
  статики.

## Структура проекта

```
RecruitFlow/
├── backend/                 # FastAPI-приложение
│   ├── app/
│   │   ├── api/             # эндпоинты: auth, users, candidates, jobs, tasks, dashboard, gdpr
│   │   ├── core/            # настройки, БД, безопасность, права, ошибки
│   │   ├── models/          # таблицы SQLAlchemy
│   │   ├── schemas/         # Pydantic-схемы
│   │   ├── services/        # бизнес-логика кандидатов
│   │   ├── main.py          # точка входа, CORS, логи, /health
│   │   └── seed.py          # демо-данные для разработки
│   ├── alembic/             # миграции
│   ├── tests/               # pytest
│   └── Dockerfile
├── frontend/                # React + Vite + Mantine, nginx в прод-образе
├── deploy/                  # Caddyfile, backup.sh, restore.sh, server-setup.md
├── docs/TZ.md               # техническое задание
├── docker-compose.yml       # dev-стек
├── docker-compose.prod.yml  # прод-стек
└── .env.example             # шаблон переменных окружения
```

## Быстрый старт локально

Нужны **Docker** и **Docker Compose v2** (проверка: `docker compose version`).

```bash
git clone <адрес-репозитория> RecruitFlow
cd RecruitFlow
docker compose up --build
```

Что поднимется:

| Адрес | Что это |
|---|---|
| http://localhost:5173 | фронтенд (dev-сервер Vite, проксирует `/api` на бэкенд) |
| http://localhost:8000 | API |
| http://localhost:8000/api/docs | Swagger UI |
| http://localhost:8000/health | health-check |
| localhost:5432 | PostgreSQL (только для локальной разработки) |

Интерфейс полностью доступен на http://localhost:5173 после `docker compose exec backend
python -m app.seed` (демо-данные и пользователи).

Миграции Alembic применяются автоматически при старте backend-контейнера. Файл `.env` для
локального запуска не обязателен — в `docker-compose.yml` заданы dev-значения по умолчанию.
Если хотите свои настройки: `cp .env.example .env` и отредактируйте.

### Демо-данные и первый вход

```bash
docker compose exec backend python -m app.seed
```

Скрипт создаст администратора, рекрутера, две вакансии и демо-кандидатов. Повторный запуск
ничего не сделает, если пользователи уже есть. Seed работает только в dev: при
`ENVIRONMENT=prod` он отказывается запускаться.

Первый вход:

- **Email:** `admin@recruitflow.local`
- **Пароль:** `Admin1234!`

Дополнительно создаётся рекрутер: `recruiter@recruitflow.local` / `Recruiter123!`.

## Тесты

Бэкенд:

```bash
cd backend
pytest
```

Перед запуском нужен PostgreSQL на `localhost:5432` (проще всего: `docker compose up -d db` из
корня проекта) и установленные зависимости из `backend/requirements.txt`. Тесты сами создают
отдельную базу `recruitflow_test`, применяют миграции и очищают таблицы между тестами.

Фронтенд (typecheck, сборка и тесты):

```bash
cd frontend
npm install
npm run build
npm test
```

## Документация

- [docs/TZ.md](docs/TZ.md) — техническое задание: требования, роли, модель данных, API,
  допущения.
- [deploy/server-setup.md](deploy/server-setup.md) — пошаговая инструкция по развёртыванию на
  VPS: домен, SSH, firewall, Docker, HTTPS, бэкапы, обновление и восстановление.

## Продакшен

Кратко: заполнить `.env` (пароль БД, `SECRET_KEY`, `DOMAIN`, `EMAIL`, `CORS_ORIGINS`) и
выполнить:

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Подробности — в [deploy/server-setup.md](deploy/server-setup.md).
