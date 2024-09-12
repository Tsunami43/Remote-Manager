#!/bin/bash
mkdir -p mnt
# Name of the virtual environment
VENV_DIR=".venv"

# Create a virtual environment
if [ ! -d "$VENV_DIR" ]; then
  echo "Creating virtual environment $VENV_DIR..."
  python3 -m venv "$VENV_DIR"
else
  echo "Virtual environment $VENV_DIR already exists."
fi

# Activate the virtual environment and install Python dependencies
source "$VENV_DIR/bin/activate"
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Deactivate the virtual environment
deactivate
