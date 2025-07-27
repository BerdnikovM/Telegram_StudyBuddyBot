import asyncio
from sqlmodel import SQLModel
from study_buddy_bot.db import engine
from study_buddy_bot.models import User, Task

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    print("✅ Все таблицы успешно созданы!")

if __name__ == "__main__":
    asyncio.run(init_db())