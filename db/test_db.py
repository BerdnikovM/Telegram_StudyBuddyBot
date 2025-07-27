# test_db.py

import asyncio
from sqlmodel import SQLModel
from study_buddy_bot.db import engine

async def test_connection():
    try:
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        print("✅ Успешное подключение к базе данных!")
    except Exception as e:
        print("❌ Ошибка при подключении:", e)

asyncio.run(test_connection())
