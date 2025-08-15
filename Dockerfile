FROM python:3.11-slim

WORKDIR /app

COPY . /app/

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Jangan set TELEGRAM_TOKEN di sini, nanti set di environment Sevalla atau docker run

CMD ["python", "bot.py"]
