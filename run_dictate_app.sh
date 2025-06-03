#!/bin/bash
# Helper script to run the dictation app directly (development mode)

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment '.venv' not found."
    echo "Please create and set up your environment first:"
    echo "  python3 -m venv .venv"
    echo "  source .venv/bin/activate"
    echo "  pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Run the app with the virtual environment's Python
echo "Running dictate_app.py..."
python3 dictate_app.py

# Deactivate virtual environment when done
deactivate
echo "Application exited." 