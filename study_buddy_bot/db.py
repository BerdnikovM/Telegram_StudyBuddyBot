from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from study_buddy_bot.config import DATABASE_URL

# Создаём асинхронный движок для подключения к PostgreSQL
engine = create_async_engine(DATABASE_URL, echo=False)

# Создаём асинхронную фабрику сессий
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Функция для получения новой сессии
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
