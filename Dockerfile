FROM python:3.12-slim

WORKDIR /app

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код бота
COPY . .

# Указываем, как запускать бота
CMD ["python", "-m", "study_buddy_bot.main"]
