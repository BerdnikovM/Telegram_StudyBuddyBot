from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from study_buddy_bot.db import AsyncSessionLocal
from study_buddy_bot.handlers.common import router
from study_buddy_bot.models import Task, User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, date


router = Router()

class AddTaskStates(StatesGroup):
    waiting_for_text = State()
    waiting_for_deadline = State()

class EditTaskStates(StatesGroup):
    waiting_for_task_number = State()
    waiting_for_edit_field = State()
    waiting_for_new_value = State()

@router.message(Command("add"))
async def add_task_state(message: Message, state: FSMContext):
    await message.answer("Введите текст задачи:")
    await state.set_state(AddTaskStates.waiting_for_text)

@router.message(AddTaskStates.waiting_for_text, F.text)
async def add_task_text(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Текст задачи не может быть пустым! Введите текст задачи:")
        return
    await state.update_data(task_text=text)
    await message.answer("Введите дедлайн в формате ГГГГ-ММ-ДД:")
    await state.set_state(AddTaskStates.waiting_for_deadline)

@router.message(AddTaskStates.waiting_for_deadline, F.text)
async def add_task_deadline(message: Message, state: FSMContext):
    try:
        input_date = message.text.strip()
        task_deadline = datetime.strptime(input_date, "%Y-%m-%d").date()
        if task_deadline < date.today():
            await message.answer("Дедлайн не может быть в прошлом! Введите корректную дату (ГГГГ-ММ-ДД):")
            return
    except ValueError:
        await message.answer("Некорректный формат даты. Введите дедлайн в формате ГГГГ-ММ-ДД:")
        return

    data = await state.get_data()
    task_text = data["task_text"]

    # Найдём пользователя по telegram_id
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Произошла ошибка: не найден пользователь. Попробуйте заново с /start.")
            await state.clear()
            return

        # Создаём задачу
        task = Task(
            user_id=user.id,
            description=task_text,
            deadline=task_deadline,
            created_at=datetime.utcnow(),
            is_done=False
        )
        session.add(task)
        await session.commit()

    await message.answer(
        f"✅ Задача добавлена!\n"
        f"Текст: <b>{task_text}</b>\n"
        f"Дедлайн: <b>{task_deadline}</b>",
        parse_mode="HTML"
    )
    await state.clear()

    # Здесь вызываем list_tasks, передаём message
    await list_tasks(message)

@router.message(Command("edit"))
async def edit_task_start(message: Message, state: FSMContext):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Укажи номер задачи для изменения: /edit <номер>")
        return
    await state.update_data(edit_task_number=int(parts[1]))
    await message.answer("Что хочешь изменить? Напиши: текст или дедлайн.")
    await state.set_state(EditTaskStates.waiting_for_edit_field)

@router.message(EditTaskStates.waiting_for_edit_field, F.text)
async def edit_task_choose_field(message: Message, state: FSMContext):
    field = message.text.strip().lower()
    if field not in ("текст", "дедлайн"):
        await message.answer("Варианты: текст или дедлайн. Попробуй ещё раз.")
        return
    await state.update_data(edit_field=field)
    if field == "текст":
        await message.answer("Введи новый текст задачи:")
    else:
        await message.answer("Введи новый дедлайн (ГГГГ-ММ-ДД):")
    await state.set_state(EditTaskStates.waiting_for_new_value)

@router.message(EditTaskStates.waiting_for_new_value, F.text)
async def edit_task_update_value(message: Message, state: FSMContext):
    data = await state.get_data()
    task_number = data["edit_task_number"]
    field = data["edit_field"]
    new_value = message.text.strip()

    # Поиск пользователя и его задач
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
            await state.clear()
            return

        stmt = (
            select(Task)
            .where(Task.user_id == user.id)
            .order_by(Task.is_done, Task.deadline)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        if not tasks or task_number < 1 or task_number > len(tasks):
            await message.answer("Некорректный номер задачи.")
            await state.clear()
            return

        task = tasks[task_number - 1]
        if field == "текст":
            if not new_value:
                await message.answer("Текст задачи не может быть пустым!")
                return
            task.description = new_value
        else:
            # Проверка формата даты
            try:
                deadline = datetime.strptime(new_value, "%Y-%m-%d").date()
                if deadline < date.today():
                    await message.answer("Дедлайн не может быть в прошлом!")
                    return
                task.deadline = deadline
            except ValueError:
                await message.answer("Неверный формат даты. Введи дедлайн в формате ГГГГ-ММ-ДД:")
                return

        await session.commit()

    await message.answer("✅ Задача успешно изменена!")
    await state.clear()
    await list_tasks(message)

@router.message(Command("delete"))
async def delete_task(message: Message):
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Укажи номер задачи для удаления: /delete <номер>")
        return
    task_number = int(parts[1])

    async with AsyncSessionLocal() as session:
        # Найти пользователя
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
            return

        # Найти задачи пользователя
        stmt = (
            select(Task)
            .where(Task.user_id == user.id)
            .order_by(Task.is_done, Task.deadline)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        if not tasks or task_number < 1 or task_number > len(tasks):
            await message.answer("Некорректный номер задачи. Используй /list чтобы узнать номер.")
            return

        task = tasks[task_number - 1]
        session.delete(task)
        await session.commit()

    await message.answer("Задача удалена.")
    await list_tasks(message)

@router.message(Command("list"))
async def list_tasks(message: Message):
    async with AsyncSessionLocal() as session:
        # Находим пользователя по telegram_id
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
            return

        # Находим все задачи пользователя, сортируем по дедлайну, невыполненные сверху
        stmt = (
            select(Task)
            .where(Task.user_id == user.id)
            .order_by(Task.is_done, Task.deadline)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        if not tasks:
            await message.answer("У тебя пока нет задач. Используй /add чтобы создать первую!")
            return

        msg = "<b>Твои задачи:</b>\n"
        for i, task in enumerate(tasks, 1):
            status = "✅" if task.is_done else "🟡"
            deadline = task.deadline.strftime("%Y-%m-%d")
            msg += f"{i}. <b>{task.description}</b> (до {deadline}) {status}\n"

        await message.answer(msg, parse_mode="HTML")

@router.message(Command("done"))
async def done_task(message: Message):
    # Ожидаем команду вида: /done 2
    parts = message.text.strip().split(maxsplit=1)
    if len(parts) < 2 or not parts[1].isdigit():
        await message.answer("Пожалуйста, укажи номер задачи из списка: /done <номер>")
        return
    task_number = int(parts[1])

    async with AsyncSessionLocal() as session:
        # Находим пользователя
        stmt = select(User).where(User.telegram_id == message.from_user.id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
            return

        # Находим задачи пользователя (сортировка — как в /list)
        stmt = (
            select(Task)
            .where(Task.user_id == user.id)
            .order_by(Task.is_done, Task.deadline)
        )
        result = await session.execute(stmt)
        tasks = result.scalars().all()

        if not tasks or task_number < 1 or task_number > len(tasks):
            await message.answer("Некорректный номер задачи. Используй /list чтобы узнать номер.")
            return

        task = tasks[task_number - 1]
        if task.is_done:
            await message.answer("Эта задача уже была отмечена как выполненная.")
            return

        task.is_done = True
        task.done_at = datetime.utcnow()
        await session.commit()

        await message.answer(f"Задача <b>{task.description}</b> отмечена как выполненная! ✅", parse_mode="HTML")
