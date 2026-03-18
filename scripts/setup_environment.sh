#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

echo "--- Setting up Python Virtual Environment ---"

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv venv
echo "Virtual environment 'venv' created."

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
echo "Virtual environment activated."

# Install dependencies including psutil
echo "Installing required Python packages (ccxt[gemini], numpy, psutil)..."
pip install ccxt[gemini] numpy psutil
echo "Dependencies installed successfully."

echo "--- Virtual Environment Setup Complete ---"
echo "You can now run the Flask app using: python3 app.py"
echo "Or the trading script using: ./crypto_trading_llm.sh"
