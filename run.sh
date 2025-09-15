#!/bin/bash

echo "Starting Safety Report Analyzer..."
echo

# Check if virtual environment exists
if [ ! -f ".venv/bin/activate" ]; then
    echo "Virtual environment not found. Running installer..."
    ./install.sh
    if [ $? -ne 0 ]; then
        exit 1
    fi
fi

echo "Activating virtual environment..."
source .venv/bin/activate

echo "Starting application..."
python gui.py
