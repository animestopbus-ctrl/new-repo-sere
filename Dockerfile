# 1. Upgrade to Python 3.12 for better Async performance
FROM python:3.12-slim

# 2. Set the working directory inside the container
WORKDIR /app

# 3. Set Timezone to IST so your logs and Database dates match your local time
ENV TZ=Asia/Kolkata
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 4. Copy requirements first (Docker caches this step to make future deployments faster)
COPY requirements.txt requirements.txt

# 5. Upgrade pip to avoid build errors, then install your bot's libraries
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 6. Copy all your modular bot files (bot.py, script.py, secret.py, database/, etc.)
COPY . .

# 7. Document the port used by your keep_alive.py Flask server
EXPOSE 8080

# 8. Ignite the engine
CMD ["python", "bot.py"]