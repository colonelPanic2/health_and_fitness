# Use an official Python base image
FROM python:3.12-slim

# Set the working directory
WORKDIR /app

# Copy project files
COPY . .

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
RUN pip install --upgrade pip && pip install -r requirements.txt

# Run the bot
CMD ["python", "discord_bot/exercise/exercise_tracker_bot.py"]

