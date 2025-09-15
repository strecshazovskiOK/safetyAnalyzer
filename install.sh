#!/bin/bash

echo "Installing Safety Report Analyzer..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is not installed"
    echo "Please install Python 3.8+ from https://python.org"
    exit 1
fi

echo "Python found. Creating virtual environment..."
python3 -m venv .venv

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "Installation complete!"
echo
echo "To run the Safety Analyzer:"
echo "1. Run: ./run.sh"
echo "2. Or run: source .venv/bin/activate && python gui.py"
echo
