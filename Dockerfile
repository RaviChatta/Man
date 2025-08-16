# Base image
FROM python:3.12-slim-bullseye

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libavif-dev \
    git \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip and related tools
RUN python -m pip install --upgrade pip setuptools wheel

# Copy and install Python dependencies
COPY requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt

# Copy the full project
COPY . /app

# Ensure start.sh is executable
RUN chmod +x start.sh

# Run the bot
CMD ["bash", "start.sh"]


