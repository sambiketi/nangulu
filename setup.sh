#!/bin/bash
set -e

echo "🐔 Setting up Nangulu Chicken Feed POS..."

# Check Python version
python_version=$(python3 --version | cut -d' ' -f2)
echo "Python version: $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from example..."
    cp .env.example .env
    echo "⚠️ Please edit .env file with your database credentials!"
fi

# Test database connection
echo "Testing database connection..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()
from app.database import test_connection
success, message = test_connection()
print(message)
if not success:
    exit(1)
"

echo "✅ Setup complete!"
echo ""
echo "To run the application:"
echo "  source venv/bin/activate"
echo "  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
echo ""
echo "Access at: http://localhost:8000"
echo "API docs: http://localhost:8000/api/docs"
