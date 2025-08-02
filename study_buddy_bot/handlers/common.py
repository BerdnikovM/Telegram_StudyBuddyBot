from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import Message
from study_buddy_bot.models import User
from study_buddy_bot.db import AsyncSessionLocal
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message):
    # Попробуем найти пользователя в БД
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if user is None:
            # Новый пользователь — регистрируем
            user = User(
                telegram_id=message.from_user.id,
                first_name=message.from_user.first_name,
                username=message.from_user.username,
                registered_at=datetime.utcnow()
            )
            session.add(user)
            await session.commit()
            text = (
                f"Привет, {message.from_user.first_name}! 👋\n"
                f"Я — StudyBuddyBot. Помогу тебе отслеживать задачи, напоминать о дедлайнах и вести статистику.\n"
                f"Отправь /help, чтобы узнать больше."
            )
        else:
            text = (
                f"С возвращением, {user.first_name or 'друг'}!\n"
                f"Готов продолжать помогать тебе в учёбе. Отправь /help для справки."
            )
        await message.answer(text)

@router.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "📚 <b>Доступные команды:</b>\n"
        "/add <текст> — добавить задачу (дедлайн — сегодня)\n"
        "/list — список твоих задач\n"
        "/done <номер> — отметить задачу выполненной\n"
        "/stats — статистика за неделю\n"
        "/help — эта справка"
    )
    await message.answer(text, parse_mode="HTML")