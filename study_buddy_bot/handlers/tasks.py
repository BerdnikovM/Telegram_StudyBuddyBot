import logging
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from study_buddy_bot.db import AsyncSessionLocal
from study_buddy_bot.models import Task, User
from sqlalchemy import select
from datetime import datetime, date, timedelta


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
    try:
        await message.answer("Введите текст задачи:")
        await state.set_state(AddTaskStates.waiting_for_text)
    except Exception:
        logging.exception("Failed to initiate add task")
        await message.answer("Упс, произошла ошибка. Попробуй позже.")


@router.message(AddTaskStates.waiting_for_text, F.text)
async def add_task_text(message: Message, state: FSMContext):
    try:
        text = message.text.strip()
        if not text:
            await message.answer("Текст задачи не может быть пустым! Введите текст задачи:")
            return
        await state.update_data(task_text=text)
        await message.answer("Введите дедлайн в формате ГГГГ-ММ-ДД:")
        await state.set_state(AddTaskStates.waiting_for_deadline)
    except Exception:
        logging.exception("Failed to process task text")
        await message.answer("Упс, произошла ошибка. Попробуй позже.")


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

    try:
        data = await state.get_data()
        task_text = data["task_text"]

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Произошла ошибка: не найден пользователь. Попробуйте заново с /start.")
                await state.clear()
                return

            task = Task(
                user_id=user.id,
                description=task_text,
                deadline=task_deadline,
                created_at=datetime.utcnow() + timedelta(hours=3),
                is_done=False,
            )
            session.add(task)
            await session.commit()

        await message.answer(
            f"✅ Задача добавлена!\n"
            f"Текст: <b>{task_text}</b>\n"
            f"Дедлайн: <b>{task_deadline}</b>",
            parse_mode="HTML",
        )
        await state.clear()
        await list_tasks(message)
    except Exception:
        logging.exception("Failed to add task")
        await message.answer("Не удалось добавить задачу. Попробуй позже.")
        await state.clear()


@router.message(Command("edit"))
async def edit_task_start(message: Message, state: FSMContext):
    try:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Укажи номер задачи для изменения: /edit &lt;номер&gt;")
            return
        await state.update_data(edit_task_number=int(parts[1]))
        await message.answer("Что хочешь изменить? Напиши: текст или дедлайн.")
        await state.set_state(EditTaskStates.waiting_for_edit_field)
    except Exception:
        logging.exception("Failed to start edit task")
        await message.answer("Упс, произошла ошибка. Попробуй позже.")


@router.message(EditTaskStates.waiting_for_edit_field, F.text)
async def edit_task_choose_field(message: Message, state: FSMContext):
    try:
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
    except Exception:
        logging.exception("Failed to choose edit field")
        await message.answer("Упс, произошла ошибка. Попробуй позже.")


@router.message(EditTaskStates.waiting_for_new_value, F.text)
async def edit_task_update_value(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        task_number = data["edit_task_number"]
        field = data["edit_field"]
        new_value = message.text.strip()

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
    except Exception:
        logging.exception("Failed to update task")
        await message.answer("Не удалось изменить задачу. Попробуй позже.")
        await state.clear()


@router.message(Command("delete"))
async def delete_task(message: Message):
    try:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Укажи номер задачи для удаления: /delete &lt;номер&gt;")
            return
        task_number = int(parts[1])

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
                return

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
            await session.delete(task)
            await session.commit()

        await message.answer("Задача удалена.")
        await list_tasks(message)
    except Exception:
        logging.exception("Failed to delete task")
        await message.answer("Не удалось удалить задачу. Попробуй позже.")


@router.message(Command("list"))
async def list_tasks(message: Message):
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
                return

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
    except Exception:
        logging.exception("Failed to list tasks")
        await message.answer("Не удалось получить список задач. Попробуй позже.")


@router.message(Command("done"))
async def done_task(message: Message):
    try:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) < 2 or not parts[1].isdigit():
            await message.answer("Пожалуйста, укажи номер задачи из списка: /done &lt;номер&gt;")
            return
        task_number = int(parts[1])

        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.telegram_id == message.from_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                await message.answer("Ошибка: пользователь не найден. Вызовите /start.")
                return

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
            task.done_at = datetime.utcnow() + timedelta(hours=3)
            await session.commit()

        await message.answer(f"Задача <b>{task.description}</b> отмечена как выполненная! ✅", parse_mode="HTML")
    except Exception:
        logging.exception("Failed to mark task done")
        await message.answer("Не удалось отметить задачу. Попробуй позже.")

