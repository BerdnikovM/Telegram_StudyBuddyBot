import asyncio
import logging
from aiogram import Bot, Dispatcher
from study_buddy_bot.config import BOT_TOKEN
from study_buddy_bot.handlers import admin, common, stats, tasks
from study_buddy_bot.scheduler import start_scheduler

# 1. Настроим логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)

def register_handlers(dp: Dispatcher):
    dp.include_router(common.router)
    dp.include_router(tasks.router)
    dp.include_router(stats.router)
    dp.include_router(admin.router)

async def main():
    # 2. Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
    dp = Dispatcher()

    # 3. Регистрируем роутеры
    register_handlers(dp)

    # 4. Запускаем планировщик (ежедневные напоминания и т.д.)
    start_scheduler(bot)

    # 5. Запускаем polling (бесконечный цикл обработки сообщений)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Бот остановлен.")
