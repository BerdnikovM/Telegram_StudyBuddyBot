import logging
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message
from study_buddy_bot.models import User, Task
from study_buddy_bot.db import AsyncSessionLocal
from sqlalchemy import select, or_
from datetime import datetime, timedelta


router = Router()


@router.message(Command("stats"))
async def stats(message: Message):
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
                return

            now = datetime.utcnow()
            week_ago = now - timedelta(days=7)

            stmt = (
                select(Task)
                .where(
                    Task.user_id == user.id,
                    or_(
                        Task.created_at >= week_ago,
                        Task.done_at >= week_ago,
                    ),
                )
            )
            result = await session.execute(stmt)
            tasks = result.scalars().all()

            added = sum(1 for t in tasks if t.created_at >= week_ago)
            done = sum(1 for t in tasks if t.is_done and t.done_at and t.done_at >= week_ago)
            open_tasks = sum(1 for t in tasks if not t.is_done and t.created_at >= week_ago)
            percent_done = f"{(done/added*100):.0f}%" if added > 0 else "—"

            msg = (
                "<b>Статистика за 7 дней:</b>\n"
                f"• Добавлено задач: <b>{added}</b>\n"
                f"• Выполнено задач: <b>{done}</b>\n"
                f"• Осталось невыполненных: <b>{open_tasks}</b>\n"
                f"• Процент выполненных: <b>{percent_done}</b>"
            )
            await message.answer(msg, parse_mode="HTML")
    except Exception:
        logging.exception("Failed to gather stats")
        await message.answer("Не удалось получить статистику. Попробуй позже.")

