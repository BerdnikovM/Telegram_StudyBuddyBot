import asyncio
import re
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from study_buddy_bot.models import User
from study_buddy_bot.db import AsyncSessionLocal
from study_buddy_bot.config import ADMINS
from sqlalchemy import select

router = Router()

batch_size = 20  # Сколько сообщений отправляем за одну пачку
delay = 1        # Пауза между пачками (секунды)

PAGE_SIZE = 10

def build_users_keyboard(page: int, total: int):
    builder = InlineKeyboardBuilder()
    if (page + 1) * PAGE_SIZE < total:
        builder.button(text="▶️ Далее", callback_data=f"users_page_{page + 1}")
    builder.button(text="❌ Выйти", callback_data="users_exit")
    return builder.as_markup()

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
        stmt = select(User).order_by(User.id)
        result = await session.execute(stmt)
        users = result.scalars().all()

    page = 0
    total = len(users)
    users_page = users[page*PAGE_SIZE:(page+1)*PAGE_SIZE]
    text = "<b>Пользователи:</b>\n"
    for u in users_page:
        text += f"id: <code>{u.telegram_id}</code> | @{u.username or '-'}\n"
    text += f"\nПоказано {page*PAGE_SIZE+1}–{page*PAGE_SIZE+len(users_page)} из {total}"

    await message.answer(
        text, parse_mode="HTML",
        reply_markup=build_users_keyboard(page, total)
    )

@router.callback_query(F.data.startswith("users_page_"))
async def users_next_page(callback: CallbackQuery):
    page = int(callback.data.split("_")[-1])

    async with AsyncSessionLocal() as session:
        stmt = select(User).order_by(User.id)
        result = await session.execute(stmt)
        users = result.scalars().all()

    total = len(users)
    users_page = users[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    text = "<b>Пользователи:</b>\n"
    for u in users_page:
        text += f"id: <code>{u.telegram_id}</code> | @{u.username or '-'}\n"
    text += f"\nПоказано {page * PAGE_SIZE + 1}–{page * PAGE_SIZE + len(users_page)} из {total}"

    await callback.message.edit_text(
        text, parse_mode="HTML",
        reply_markup=build_users_keyboard(page, total)
    )
    await callback.answer()

@router.callback_query(F.data == "users_exit")
async def users_exit(callback: CallbackQuery):
    await callback.message.edit_text("Просмотр пользователей завершён.")
    await callback.answer()

@router.message(Command("broadcast"))
async def broadcast(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔️ У тебя нет прав для этой команды.")
        return

    # Пример:
    # /broadcast ids=123,456, 789 text=Привет!
    # /broadcast text=Привет всем!
    cmd = message.text[len("/broadcast"):].strip()

    ids = None
    text = None

    # 1. Пытаемся найти ids=
    m = re.search(r'ids\s*=\s*([^\s]+)', cmd)
    if m:
        # Собрали строку id
        raw_ids = m.group(1)
        # Удаляем пробелы вокруг id и разделяем по запятой
        ids = []
        for part in raw_ids.split(","):
            s = part.strip()
            if not s.isdigit():
                await message.answer(f"Некорректный id: '{s}'. Все id должны быть числами.")
                return
            ids.append(int(s))
        # Обрезаем найденный кусок, чтобы дальше искать text=
        cmd = cmd.replace(m.group(0), '').strip()

    # 2. Находим text=
    m_text = re.search(r'text\s*=\s*(.+)', cmd)
    if m_text:
        text = m_text.group(1).strip()
    elif not ids:  # Если ids нет — значит, всё сообщение — это текст
        text = cmd.strip()
    else:
        await message.answer("Не найден аргумент text=. Пример:\n/broadcast ids=123,456 text=Сообщение")
        return

    if not text:
        await message.answer("Текст сообщения не должен быть пустым.")
        return

    # Получаем пользователей
    async with AsyncSessionLocal() as session:
        stmt = select(User)
        if ids:
            stmt = stmt.where(User.telegram_id.in_(ids))
        result = await session.execute(stmt)
        users = result.scalars().all()

    # Проверяем, что указанные id реально есть в базе
    invalid_ids = []
    if ids:
        users_id_set = {u.telegram_id for u in users}
        invalid_ids = [uid for uid in ids if uid not in users_id_set]

    count = 0
    failed = []

    for i in range(0, len(users), batch_size):
        batch = users[i:i + batch_size]
        tasks = [safe_send(message.bot, user.telegram_id, text) for user in batch]
        results = await asyncio.gather(*tasks)
        for idx, ok in enumerate(results):
            if ok:
                count += 1
            else:
                failed.append(batch[idx].telegram_id)
        await asyncio.sleep(delay)

    reply = f"Сообщение отправлено {count} пользователям."
    if failed:
        reply += "\n❗️ Не удалось доставить:\n" + ", ".join(str(uid) for uid in failed)
    if invalid_ids:
        reply += "\n‼️ Эти id не зарегистрированы в системе:\n" + ", ".join(str(uid) for uid in invalid_ids)
    await message.answer(reply)