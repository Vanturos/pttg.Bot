FROM python:3.8.10
RUN apt-get update && apt-get install -y \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /telegram-bot-app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . . 
CMD ["python3", "bot.py"]
