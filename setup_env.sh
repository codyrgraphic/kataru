#!/bin/bash
# Script to set up the virtual environment and install dependencies

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment already exists
if [ -d ".venv" ]; then
    read -p "Virtual environment '.venv' already exists. Do you want to recreate it? (y/n): " recreate
    if [ "$recreate" = "y" ]; then
        echo "Removing existing virtual environment..."
        rm -rf .venv
    else
        echo "Using existing virtual environment."
        source .venv/bin/activate
        if ! python3 -c "import pip" &>/dev/null; then
            echo "Error: pip not available in the virtual environment."
            echo "Consider recreating the virtual environment."
            exit 1
        fi
        echo "Updating dependencies..."
        pip install -r requirements.txt
        echo "Environment setup complete."
        exit 0
    fi
fi

# Create virtual environment
echo "Creating virtual environment..."
python3 -m venv .venv
if [ $? -ne 0 ]; then
    echo "Failed to create virtual environment. Please check your Python installation."
    exit 1
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
# Ensure pip is available and updated
python3 -m pip install --upgrade pip

# Install from requirements.txt
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please check requirements.txt."
        exit 1
    fi
else
    echo "Warning: requirements.txt not found. Creating a basic one..."
    cat > requirements.txt << EOF
rumps>=0.4.0
sounddevice>=0.4.5
pynput>=1.7.6
scipy>=1.9.0
numpy>=1.22.0
configparser>=5.3.0
PyObjC>=9.0.1
EOF
    pip install -r requirements.txt
fi

echo "Virtual environment '$VENV_DIR' is set up and dependencies are installed."
echo "Activate it using: source $VENV_DIR/bin/activate"

exit 0