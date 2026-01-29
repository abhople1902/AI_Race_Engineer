#!/bin/bash

# Script to run main.py using venv (without Docker)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
VENV_DIR="$SCRIPT_DIR/venv"

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install/upgrade requirements
echo "Installing requirements..."
pip install --upgrade pip
pip install -r "$SCRIPT_DIR/requirements.txt"

# Run main.py from the app directory
echo "Running main.py..."
cd "$SCRIPT_DIR/app"
python main.py

