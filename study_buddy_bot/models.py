from typing import Optional
from datetime import datetime, date
from sqlmodel import SQLModel, Field, Relationship

class User(SQLModel, table=True):
    """
    Модель пользователя Telegram.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(index=True, unique=True)
    first_name: Optional[str] = Field(default=None)
    username: Optional[str] = Field(default=None)
    is_admin: bool = Field(default=False)
    registered_at: datetime = Field(default_factory=datetime.utcnow)

    # Связь: один пользователь — много задач
    tasks: list["Task"] = Relationship(back_populates="user")

class Task(SQLModel, table=True):
    """
    Модель учебной задачи.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    description: str
    deadline: date
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_done: bool = Field(default=False)
    done_at: Optional[datetime] = None

    # Связь: задача принадлежит пользователю
    user: Optional[User] = Relationship(back_populates="tasks")
