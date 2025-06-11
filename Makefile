# Makefile for Kataru

# Variables
PYTHON = python3
VENV_DIR = .venv
VENV_PYTHON = $(VENV_DIR)/bin/python
VENV_PIP = $(VENV_DIR)/bin/pip
WHISPER_CPP_DIR = whisper.cpp
WHISPER_CPP_BUILD_DIR = $(WHISPER_CPP_DIR)/build
WHISPER_CPP_MODEL_DIR = $(WHISPER_CPP_DIR)/models
WHISPER_MODEL_NAME = ggml-small.en.bin
WHISPER_MODEL_PATH = $(WHISPER_CPP_MODEL_DIR)/$(WHISPER_MODEL_NAME)
DIST_DIR = dist
APP_BUNDLE_NAME = Kataru.app
APP_BUNDLE_PATH = $(DIST_DIR)/$(APP_BUNDLE_NAME)

# DMG Creation Variables
VERSION = $(shell $(VENV_PYTHON) -c "exec(open('version.py').read()); print(__version__)" 2>/dev/null || echo "0.1.3")
DMG_NAME = Kataru-$(VERSION)
DMG_STAGING_DIR = $(DIST_DIR)/dmg_staging
DMG_OUTPUT = $(DIST_DIR)/$(DMG_NAME).dmg

# Phony targets are not files
.PHONY: all setup build_whisper_cpp build_app run run_dev clean clean_venv test build_dmg

# Default target
all: $(APP_BUNDLE_PATH)

# Setup Python virtual environment and install dependencies
$(VENV_DIR)/bin/activate: requirements.txt
	@if [ ! -d "$(VENV_DIR)" ]; then \
		echo "Creating virtual environment in $(VENV_DIR)..."; \
		$(PYTHON) -m venv $(VENV_DIR); \
	fi
	@echo "Installing/updating dependencies from requirements.txt...";
	@$(VENV_PIP) install --upgrade pip;
	@$(VENV_PIP) install -r requirements.txt;
	@touch $(VENV_DIR)/bin/activate # Mark as updated

setup: $(VENV_DIR)/bin/activate
	@echo "Python environment is ready in $(VENV_DIR)"

# Build whisper.cpp and download model
# Stamp file to indicate whisper.cpp is built and model is downloaded
WHISPER_CPP_STAMP = $(WHISPER_CPP_BUILD_DIR)/.whisper_built_and_model_downloaded

$(WHISPER_CPP_STAMP):
	@echo "Building whisper.cpp and downloading model..."
	@if [ ! -f "$(WHISPER_CPP_DIR)/CMakeLists.txt" ]; then \
		echo "Error: whisper.cpp submodule not found or not initialized."; \
		echo "Please run: git submodule update --init --recursive"; \
		exit 1; \
	fi
	@cd $(WHISPER_CPP_DIR) && rm -rf build # Clean build
	@cd $(WHISPER_CPP_DIR) && cmake -B build -DGGML_METAL=ON
	@cd $(WHISPER_CPP_DIR) && cmake --build build --config Release -j
	@echo "Downloading Whisper model $(WHISPER_MODEL_NAME)..."
	@cd $(WHISPER_CPP_MODEL_DIR) && bash download-ggml-model.sh $(WHISPER_MODEL_NAME:ggml-%.en.bin=%.en)
	@ # Check if model downloaded successfully
	@if [ ! -f "$(WHISPER_MODEL_PATH)" ]; then \
		echo "Error: Whisper model download failed. $(WHISPER_MODEL_PATH) not found."; \
		exit 1; \
	fi
	@echo "whisper.cpp build and model download complete."
	@touch $(WHISPER_CPP_STAMP)

build_whisper_cpp: $(WHISPER_CPP_STAMP)
	@echo "whisper.cpp is built and model is available."

# Build the application bundle
$(APP_BUNDLE_PATH): Kataru.spec dictate_app.py version.py australian_english_conversions.py $(WHISPER_CPP_STAMP) $(VENV_DIR)/bin/activate
	@echo "Cleaning up previous PyInstaller build directories (build/ and dist/)..."
	@rm -rf ./build $(DIST_DIR) # Note: ./build is PyInstaller's, not whisper.cpp/build
	@echo "Building application bundle with PyInstaller..."
	$(VENV_PYTHON) -m PyInstaller Kataru.spec --noconfirm
	@if [ ! -d "$(APP_BUNDLE_PATH)" ]; then \
		echo "Error: PyInstaller build failed. App bundle not found at $(APP_BUNDLE_PATH)."; \
		exit 1; \
	fi
	@echo "Signing app bundle with entitlements..."
	@if security find-identity -v -p codesigning | grep -q "Developer ID Application"; then \
		echo "Signing with Developer ID certificate..."; \
		codesign --force --sign "Developer ID Application" --entitlements Kataru.entitlements --options runtime $(APP_BUNDLE_PATH); \
	else \
		echo "No Developer ID found - signing with ad-hoc signature"; \
		codesign --force --sign - --entitlements Kataru.entitlements $(APP_BUNDLE_PATH); \
	fi
	@echo "Application bundle created and signed at $(APP_BUNDLE_PATH)"

build_app: $(APP_BUNDLE_PATH)
	@echo "Application bundle is built."

run: $(APP_BUNDLE_PATH) # Ensure app is built before running
	@echo "Launching application bundle $(APP_BUNDLE_PATH)..."
	@open $(APP_BUNDLE_PATH)

run_dev: $(VENV_DIR)/bin/activate # Ensure venv and dependencies are set up
	@echo "Running dictate_app.py in development mode (from $(VENV_DIR))..."
	@echo "(Unsetting PYTHONPATH for this run to avoid conflicts)"
	@PYTHONPATH=\"\" $(VENV_PYTHON) dictate_app.py

clean_venv: # This is mostly for internal use by the clean target now
	@echo "Removing virtual environment $(VENV_DIR)..."
	@rm -rf $(VENV_DIR)

clean:
	@echo "Cleaning all build artifacts..."
	@echo "Removing virtual environment $(VENV_DIR)..."
	@rm -rf $(VENV_DIR)
	@echo "Removing PyInstaller build artifacts (./build/ and $(DIST_DIR)/)..."
	@rm -rf ./build $(DIST_DIR) $(DMG_STAGING_DIR)
	@echo "Removing whisper.cpp build artifacts ($(WHISPER_CPP_BUILD_DIR)/)..."
	@rm -rf $(WHISPER_CPP_BUILD_DIR)
	@echo "Removing __pycache__ directories and .pyc files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + || true # Continue if none found
	@find . -type f -name "*.pyc" -delete || true # Continue if none found
	@echo "Clean complete."

# Test target (for now, just a placeholder)
test:
	@echo "Running tests... (No tests defined yet)"

# DMG Creation Target
$(DMG_OUTPUT): $(APP_BUNDLE_PATH)
	@echo "Creating professional DMG installer - this will take 2-5 minutes for large app (~548MB)"
	@echo "Progress: [1/5] Cleaning previous builds..."
	@rm -rf $(DMG_STAGING_DIR) $(DMG_OUTPUT)
	@mkdir -p $(DMG_STAGING_DIR)
	@echo "Progress: [2/5] Copying app bundle ($(shell du -sh $(APP_BUNDLE_PATH) | cut -f1 2>/dev/null || echo 'calculating...'))..."
	@cp -R $(APP_BUNDLE_PATH) $(DMG_STAGING_DIR)/
	@cp assets/Privacy_Setup_Guide.txt $(DMG_STAGING_DIR)/ 2>/dev/null || echo "Note: Privacy guide not found"
	@echo "Progress: [3/5] Setting up DMG structure..."
	@echo "Progress: [4/5] Creating DMG (this may take several minutes)..."
	create-dmg \
		--volname "Kataru $(VERSION)" \
		--volicon "assets/kataru_app_icon.icns" \
		--window-pos 200 120 \
		--window-size 800 450 \
		--icon-size 128 \
		--icon "Kataru.app" 200 190 \
		--icon "Privacy_Setup_Guide.txt" 200 320 \
		--hide-extension "Kataru.app" \
		--app-drop-link 600 190 \
		--hdiutil-quiet \
		$(DMG_OUTPUT) \
		$(DMG_STAGING_DIR)
	@echo "Progress: [5/5] DMG creation complete!"
	@echo "Final DMG: $(DMG_OUTPUT) ($(shell du -sh $(DMG_OUTPUT) | cut -f1 2>/dev/null || echo 'done'))"
	@rm -rf $(DMG_STAGING_DIR)

# Build targets
build_dmg: $(DMG_OUTPUT)
all: $(APP_BUNDLE_PATH) $(DMG_OUTPUT) 