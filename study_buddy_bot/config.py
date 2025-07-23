import os
from dotenv import load_dotenv

load_dotenv()   # загружает переменные из .env

BOT_TOKEN = os.getenv("BOT_TOKEN")

DATABASE_URL = os.getenv("DATABASE_URL")

# Админы: список int, даже если .env содержит строку
ADMINS = list(map(int, os.getenv("ADMINS", "").split(",")))
