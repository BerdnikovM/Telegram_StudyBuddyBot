import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from aiogram import Bot
from study_buddy_bot.models import User, Task
from study_buddy_bot.db import AsyncSessionLocal
from sqlalchemy import select

scheduler = AsyncIOScheduler()

async def notify_tomorrows_tasks(bot: Bot):
    """
    Рассылает всем пользователям их задачи на завтра.
    """
    tomorrow = (datetime.utcnow() + timedelta(days=1)).date()
    async with AsyncSessionLocal() as session:
        # Получаем всех пользователей
        users_stmt = select(User)
        users_result = await session.execute(users_stmt)
        users = users_result.scalars().all()

        for user in users:
            # Получаем задачи пользователя с дедлайном на завтра и статусом "не выполнено"
            tasks_stmt = (
                select(Task)
                .where(
                    Task.user_id == user.id,
                    Task.deadline == tomorrow,
                    Task.is_done == False
                )
            )
            tasks_result = await session.execute(tasks_stmt)
            tasks = tasks_result.scalars().all()

            if tasks:
                msg = "<b>Твои задачи на завтра:</b>\n"
                for t in tasks:
                    msg += f"• {t.description}\n"
                try:
                    await bot.send_message(user.telegram_id, msg, parse_mode="HTML")
                except Exception:
                    logging.exception("[Scheduler] Не удалось отправить %s", user.telegram_id)
                    continue

def start_scheduler(bot: Bot):
    """
    Запускает планировщик и добавляет ежедневную задачу на 19:00 (UTC).
    """
    scheduler.add_job(
        notify_tomorrows_tasks,
        "cron",
        [bot],
        hour=19, minute=0
    )
    scheduler.start()
    logging.info("[Scheduler] Запущен ежедневный планировщик рассылки задач на завтра.")
