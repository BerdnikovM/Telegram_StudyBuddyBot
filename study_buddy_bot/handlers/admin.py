import asyncio
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from study_buddy_bot.models import User
from study_buddy_bot.db import AsyncSessionLocal
from study_buddy_bot.config import ADMINS
from sqlalchemy import select

router = Router()

batch_size = 20  # Сколько сообщений отправляем за одну пачку
delay = 1        # Пауза между пачками (секунды)

def is_admin(user_id: int) -> bool:
    return user_id in ADMINS

async def safe_send(bot, user_id, text):
    try:
        await bot.send_message(user_id, text)
        return True
    except (TelegramForbiddenError, TelegramBadRequest):
        print(f"Пользователь {user_id} недоступен для рассылки.")
        return False
    except Exception as e:
        print(f"Ошибка при отправке {user_id}: {e}")
        return False

@router.message(Command("users"))
async def users_count(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У тебя нет прав для этой команды.")
        return

    async with AsyncSessionLocal() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()
        await message.answer(f"Всего пользователей в системе: <b>{len(users)}</b>", parse_mode="HTML")

@router.message(Command("broadcast"))
async def broadcast(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У тебя нет прав для этой команды.")
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Используй: /broadcast <текст сообщения>")
        return
    text = parts[1]

    async with AsyncSessionLocal() as session:
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

    count = 0

    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        tasks = [safe_send(message.bot, user.telegram_id, text) for user in batch]
        results = await asyncio.gather(*tasks)
        count += sum(results)
        await asyncio.sleep(delay)  # Пауза между пачками

    await message.answer(f"Сообщение отправлено {count} пользователям.")