# 1. Use the official Python image
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 🔥 3. CRITICAL FIX: Install 'gcc' and C-dependencies so TgCrypto can build successfully!
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 4. Copy the requirements file first (for caching)
COPY requirements.txt .

# 5. Upgrade pip and install all Python libraries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy the rest of your bot's code into the container
COPY . .

# 7. Start the bot
CMD ["python", "bot.py"]
