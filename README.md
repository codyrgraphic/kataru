# Kataru

A macOS menu bar app for dictation using Whisper.cpp. Press and hold a hotkey (default F5) to record audio, and release the hotkey to transcribe the audio and paste it into the active application.

## Features

- Press and hold a hotkey (default: F5) to record audio
- Release the hotkey to transcribe the recorded audio
- Transcribed text is automatically pasted at the cursor position
- Menu bar icon changes to indicate recording status
- Configurable via `config.ini`
- Works with minimal latency using local Whisper models
- Supports both direct execution (development) and bundled app (distribution) modes

## Installation

### Prerequisites

- macOS
- Python 3.11+ (recommended)
- Compiled Whisper.cpp repository (see below)
- Whisper model file (e.g., ggml-small.en.bin)

### Setup from Source

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/speech-to-text.git
   cd speech-to-text
   ```

2. Clone and build Whisper.cpp with Metal support:
   ```bash
   git clone https://github.com/ggerganov/whisper.cpp.git
   cd whisper.cpp
   cmake -B build -DGGML_METAL=ON
   cmake --build build --config Release -j
   cd ..
   ```

3. Download a Whisper model:
   ```bash
   cd whisper.cpp/models
   bash download-ggml-model.sh small.en
   cd ../..
   ```

4. Run the setup script to create a virtual environment and install dependencies:
   ```bash
   ./setup_env.sh
   ```
   
   Or manually set up the environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

5. Edit `config.ini` if needed (path configuration is usually automatic)

## Running the Application

### Development Mode

Before running in development mode, ensure no conflicting Python environment variables are set:

```bash
# Check for environment variables that may cause conflicts
env | grep PYTHON

# If present, unset these variables
unset PYTHONPATH
unset PYTHONHOME
unset PYTHONUNBUFFERED
unset PYTHONDONTWRITEBYTECODE
```

Then run the application using the provided script:

```bash
./run_dictate_app.sh
```

Or manually activate the virtual environment and run:

```bash
source .venv/bin/activate
python3 dictate_app.py
```

### Build and Run as a Standalone App

1. Use the build script to create the application bundle:
   ```bash
   ./build_app.sh
   ```

2. Run the bundled application:
   ```bash
   open dist/Kataru.app
   ```

## Configuration

The application is configured via `config.ini`:

```ini
[Paths]
# Directory containing the compiled whisper.cpp repository
whisper_cpp_dir = ./whisper.cpp

# Filename of the whisper model within the whisper.cpp/models directory
model_name = ggml-small.en.bin

# Directory containing icon files
assets_dir = ./assets

[Audio]
sample_rate = 16000
channels = 1
# Use -1 for default input device, or a specific index
device_index = 4

[Hotkey]
# Define the hotkey (e.g., f5, cmd_r, shift)
key = f5

[Icons]
# Filenames within assets_dir
icon_default = icon_default.png
icon_active = icon_active.png

[Whisper]
# Timeout for the whisper-cli transcription process in seconds
timeout_seconds = 60
# Number of CPU threads for whisper-cli to use
num_threads = 4
```

## Architecture

The application uses a clean architecture that supports both direct execution (for development) and bundled execution (for distribution):

1. **Execution Mode Detection**: The app detects whether it's running as a script or a bundled app using `hasattr(sys, 'frozen')`.

2. **PortAudio Integration**: 
   - In direct script execution mode: Dynamically locates and pre-loads the PortAudio library
   - In bundled mode: Uses the PortAudio library included in the app bundle

3. **Path Management**:
   - Script mode: Uses paths relative to the script file
   - Bundle mode: Uses paths within the app bundle's Resources directory

4. **Resource Handling**: Locates configuration files, models, executables, and icons based on execution context

5. **App Components**:
   - Menu bar application (rumps)
   - Audio recording (sounddevice)
   - Hotkey detection (pynput)
   - Whisper transcription (whisper.cpp via subprocess)
   - Text insertion via AppleScript

## Troubleshooting

### Python Environment Variable Conflicts

If you've previously used other Python bundling tools with this project directory, or if you suspect conflicting Python environment variables set by other processes, you may encounter errors when trying to run the script directly (e.g., `ModuleNotFoundError: No module named 'encodings'`).

Check if these variables are set:
```bash
env | grep PYTHON
```

If you see variables like `PYTHONHOME` or `PYTHONPATH` pointing to your app bundle, unset them:
```bash
unset PYTHONPATH
unset PYTHONHOME
unset PYTHONUNBUFFERED
unset PYTHONDONTWRITEBYTECODE
```

### Permissions

The application requires the following permissions on macOS. The app should prompt you for these when first run or when the feature is first used. If issues persist, check **System Settings > Privacy & Security**:

- **Microphone Access**: Required to record audio for transcription.
    - Look for Kataru under the "Microphone" section.
- **Input Monitoring**: Required for the global hotkey (e.g., F5) to detect key presses and releases when Kataru is not the frontmost application.
    - Look for Kataru (or potentially your terminal/Python if running in dev mode and it was launched from there) under the "Input Monitoring" section.
- **Accessibility**: May be required for reliable hotkey detection or if future features involve more complex UI interactions. Also, `pynput` sometimes requires this for listening to global hotkeys.
    - Look for Kataru under the "Accessibility" section.
- **Automation**: Required for pasting transcribed text into other applications using AppleScript.
    - Look for Kataru under the "Automation" section, specifically allowing it to control "System Events" or other target applications.

**Important:**
- If you deny a permission initially, you may need to manually enable it in System Settings.
- Sometimes, toggling the permission off and on again for the app can resolve issues.
- You might need to restart Kataru after granting permissions for them to take full effect.

If permissions are denied or not configured correctly, features like hotkey detection, recording, or pasting will not function as expected.

### Audio Device Selection

If audio recording isn't working correctly:

1. Use the "List Audio Devices" menu option to see available devices
2. Use the "Change Audio Device" menu option to select a different input device
3. The selected device index will be saved to `config.ini`

### Metal Support

For best performance, ensure Metal support is enabled when compiling whisper.cpp:
```bash
cmake -DGGML_METAL=ON ..
```

You should see Metal-related messages in the console output during transcription.

## License

[Specify your license here] 