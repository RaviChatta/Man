#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Run database or other updates
python3 update.py

# Start the bot
python3 -B main.py
