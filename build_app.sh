#!/bin/bash
# Script to build the Kataru app bundle using PyInstaller

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment '.venv' not found. Creating..."
    python3 -m venv .venv
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment. Please check your Python installation."
        exit 1
    fi
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Ensure pip is installed and up to date
echo "Ensuring pip is installed and up to date..."
python3 -m pip install --upgrade pip

# Install dependencies if needed
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies. Please check requirements.txt."
        deactivate
        exit 1
    fi
else
    echo "Warning: requirements.txt not found. Dependencies may be missing."
fi

# Clean up previous build directories used by PyInstaller
echo "Cleaning up previous build..."
rm -rf build dist

# Build whisper.cpp libraries before running PyInstaller
echo "Building whisper.cpp libraries..."
pushd whisper.cpp
# Remove existing build directory for a clean build (optional but recommended)
rm -rf build/
cmake -B build -DGGML_METAL=ON # Enable Metal for M1/M2/M3 Macs
if [ $? -ne 0 ]; then
    echo "Error: CMake configuration for whisper.cpp failed."
    popd
    deactivate
    exit 1
fi
# Build using CMake
cmake --build build --config Release
if [ $? -ne 0 ]; then
    echo "Error: CMake build for whisper.cpp failed."
    popd
    deactivate
    exit 1
fi
popd
echo "whisper.cpp build finished."

# --- Build the application bundle using PyInstaller ---
echo "Building application bundle with PyInstaller (using spec file)..."
SPEC_FILE="Kataru.spec"

if [ ! -f "$SPEC_FILE" ]; then
    echo "Error: Spec file '$SPEC_FILE' not found. Cannot build."
    deactivate
    exit 1
fi

pyinstaller "$SPEC_FILE" --noconfirm
if [ $? -ne 0 ]; then
    echo "Error: PyInstaller build failed."
    deactivate
    exit 1
fi

# --- Define final App Bundle Path ---
APP_NAME="Kataru"
APP_BUNDLE="dist/${APP_NAME}.app"

if [ ! -d "$APP_BUNDLE" ]; then
    echo "Error: App bundle '$APP_BUNDLE' not found after PyInstaller step. Build failed."
    deactivate
    exit 1
fi

# --- Manual Codesign Step (NO Hardened Runtime) ---
DEV_ID="Developer ID Application: Cody Roberts (6L458UBN7J)" # Replace if needed

if [ -n "$DEV_ID" ]; then
    echo "Signing the application bundle with identity (NO Hardened Runtime): $DEV_ID..."
    # Use --deep for bundles, omit --options=runtime
    codesign --force --deep --sign "$DEV_ID" "$APP_BUNDLE"

    if [ $? -ne 0 ]; then
        echo "Error: Failed to sign the application bundle with specific identity."
    else
        echo "Application bundle signed successfully (without Hardened Runtime)."
        # Verify signature
        echo "Verifying codesign..."
        codesign --verify --verbose=4 "$APP_BUNDLE"
        echo "Verifying Gatekeeper acceptance..."
        spctl --assess --verbose=4 --type execute "$APP_BUNDLE"
    fi
else
    echo "Warning: No specific Developer ID found or provided in script."
    echo "App bundle relies on PyInstaller's default (ad-hoc) signing."
    echo "Verifying ad-hoc signature..."
    codesign --verify --verbose=4 "$APP_BUNDLE"
fi

# Check if build was successful
if [ -d "$APP_BUNDLE" ]; then
    echo "Build successful!"
    echo "Application bundle created at: $APP_BUNDLE"
    echo "You can run it with: open \"$APP_BUNDLE\""
else
    echo "Build failed. Check the logs for errors."
fi

# Deactivate virtual environment
deactivate
echo "Build script finished."

# --- REMOVED py2app specific sections ---
# --- REMOVED Manual Python Framework Copy ---
# --- REMOVED install_name_tool section (Handled differently by PyInstaller) ---

echo ""
echo "----------------------------------------------------------------------"
echo "Build process completed."
echo "App Name: ${APP_NAME}"
echo "App Bundle: ${APP_BUNDLE}"
echo "You can now find the application bundle in the 'dist' directory."
echo "To run: open "${APP_BUNDLE}""
echo "----------------------------------------------------------------------"

exit 0 