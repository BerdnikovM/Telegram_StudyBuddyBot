# 🎓 StudyBuddyBot (aiogram 3 + SQLModel + Docker)

> **Telegram-бот для учёбы и продуктивности:** добавляй задачи, отмечай выполнение, получай напоминания и веди статистику за неделю.  
> Полностью асинхронная архитектура, современные подходы к архитектуре Telegram-ботов, чистая работа с базой данных и продвинутый DevOps-пайплайн.

<p align="center">
  <img src="docs/example1.gif" width="720">
  <img src="docs/example2.gif" width="720">
</p>

[![Docker Pulls](https://img.shields.io/docker/pulls/mihailberd/studybuddybot)](https://hub.docker.com/r/mihailberd/studybuddybot)
[![License](https://img.shields.io/github/license/BerdnikovM/Telegram_StudyBuddyBot)](LICENSE)

---

## ✨ Ключевые фичи

| Фича | Описание/Преимущество                                  |
|------|--------------------------------------------------------|
| **Асинхронный aiogram 3** | Современный FSM, Router, безопасная обработка апдейтов |
| **Управление задачами** | /add, /list, /done, /edit, /delete — CRUD-интерфейс    |
| **Умные напоминания** | Ежедневно в 19:00 MSK                                  |
| **Персональная статистика** | /stats: продуктивность за последние 7 дней              |
| **База данных SQLModel** | Чистая архитектура: User, Task. Postgres-ready          |
| **Админ-панель** | /users — просмотр, /broadcast — рассылка               |
| **RBAC для админов** | Только указанные ID могут пользоваться админ-командами          |
| **Деплой в Docker** | Полная изоляция: просто, быстро, безопасно          |
| **Готов к cloud‑деплою** | Тестировано на Timeweb, Render, любой VPS          |

---

## 🚀 Быстрый старт

> Требования: Docker 20.10+, Telegram Bot API токен, PostgreSQL (или SQLite для локального теста)

```
# 1. Создайте `.env` в любой удобной папке (см. .env.example), создайте docker-compose.yml там же.

# 2. Запустите файл:
docker compose up -d

# 3. Готово! Бот будет работать на сервере — все переменные загрузятся из `.env`.
```
> 💡 **Важно:**  
> Контейнеру нужна PostgreSQL.  
> БД можно поднять через Docker (пример см. ниже) или использовать существующую.

**docker-compose.yml (пример):**
```
version: "3.9"

services:
  db:
    image: postgres:16
    container_name: studybuddy_postgres
    restart: always
    environment:
      POSTGRES_USER: myuser         # <-- измените имя пользователя
      POSTGRES_PASSWORD: mypassword # <-- измените пароль
      POSTGRES_DB: mydb             # <-- измените имя БД
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"  # Открывает порт для локального доступа (можно убрать на сервере)
    
  init_db:
    image: mihailberd/studybuddybot:latest 
    depends_on:
      - db
    env_file:
      - .env
    command: python -m db.init_db
    
  bot:
    image: mihailberd/studybuddybot:latest
    container_name: studybuddybot
    restart: always
    env_file:
      - .env
    depends_on:
      - db
      - init_db

volumes:
  postgres_data:

```

---
## 🛠️ Стек и архитектура

| Слой               | Технологии                                   |
| ------------------ | -------------------------------------------- |
| 🐍 Язык            | **Python 3.12**                              |
| 🤖 Telegram SDK    | **aiogram 3** (Router, Filters, FSM)         |
| 🗃️ ORM/БД         | **SQLModel** + **PostgreSQL**     |
| ⏰ Планировщик      | **APScheduler**                              |
| 🐋 Контейнеризация | **Docker** / **docker-compose**              |
| 🔐 Secrets         | ENV‑переменные: токен, база, админы (`.env`) |
| 🧪 Тесты (roadmap) | **pytest-asyncio**, GitHub Actions CI        |
| ☁️ Деплой          | Timeweb Cloud, Render, любой VPS             |

---

## 🤝 Связаться

|            | Контакт                                                                  |
| ---------- |--------------------------------------------------------------------------|
| ✉ Telegram | [@MihailBerd](https://t.me/MihailBerd)                                 |
| 💼 Kwork   | [https://kwork.ru/user/berdnikovmiha) |
| 📧 Email   | [MihailBerdWork@ya.ru](mailto:MihailBerdWork@ya.ru)                                |
