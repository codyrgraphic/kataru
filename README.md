# Kataru

A macOS menu bar app for dictation using Whisper.cpp. Press and hold a hotkey (default F5) to record audio, and release the hotkey to transcribe the audio and paste it into the active application.

## Features

- Press and hold a hotkey (default: F5) to record audio
- Release the hotkey to transcribe the recorded audio
- Transcribed text is automatically pasted at the cursor position
- Menu bar icon changes to indicate recording status
- **Intelligent microphone management** with preference-based automatic selection
- **Automatic device monitoring** with sleep/wake event handling to detect microphone changes
- **Smart fallback logic** that automatically switches to alternative microphones when devices become unavailable
- Menu bar microphone selection with priority scoring based on device preferences
- Configurable via `config.ini`
- Works with minimal latency using local Whisper models
- Supports both direct execution (development) and bundled app (distribution) modes

## Prerequisites

- **macOS**
- **Git:** For cloning the repository.
- **Homebrew (Recommended):** For easily installing `git-lfs` and other tools.
  - Install Homebrew if not present: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
- **Xcode Command Line Tools:** Needed for compiling `whisper.cpp` (a C++ project). Install with `xcode-select --install` if you haven't already.
- **Python 3.11+:** Ensure Python 3.11 or a newer version is installed and accessible as `python3`.

## Setup, Build, and Run using Makefile

This project uses a `Makefile` to simplify the setup, build, and execution process.

1.  **Clone the Repository:**
    Open your terminal and run the following commands. The `--recurse-submodules` flag is important as it will also clone the `whisper.cpp` submodule.
    ```bash
    git clone --recurse-submodules git@github.com:codyrgraphic/kataru.git
    cd kataru
    ```
    *(If you prefer HTTPS: `git clone --recurse-submodules https://github.com/codyrgraphic/kataru.git`)*

2.  **Install Git LFS (First-time setup per user):**
    Git LFS helps manage large files. While the main model is in the submodule, LFS is good practice for the project.
    ```bash
    brew install git-lfs
    git lfs install # Initializes Git LFS for your user account (run once)
    ```

3.  **Build Everything (Initial Setup & App Bundling):**
    This single command will:
    - Set up the Python virtual environment (`.venv/`).
    - Install all required Python dependencies.
    - Compile the `whisper.cpp` submodule with Metal support (for M1/M2/M3 Macs).
    - Download the `ggml-small.en.bin` speech recognition model.
    - Build the `Kataru.app` application bundle in the `dist/` directory.
    ```bash
    make all
    ```
    This command may take a few minutes the first time, especially during the `whisper.cpp` compilation.

4.  **Run the Application:**

    *   **Run the Bundled App (Recommended for General Use):**
        ```bash
        make run
        ```
        Alternatively, you can directly open the app:
        ```bash
        open dist/Kataru.app
        ```
        On the first launch, macOS will likely prompt you to grant necessary permissions for:
        - **Microphone Access:** For recording audio.
        - **Accessibility Permissions:** For global hotkey detection.
        - **Automation (System Events):** For pasting transcribed text.
        Please grant these permissions when asked. You can manage them later in **System Settings > Privacy & Security**. If the hotkey doesn't work immediately, try toggling the Accessibility permission for Kataru off and on, or even removing and re-adding Kataru to the Accessibility list.

    *   **Run in Development Mode (Directly from scripts):**
        This is useful for debugging or making live code changes without rebuilding the entire bundle.
        ```bash
        make run_dev
        ```
        This command runs `python3 dictate_app.py` using the project's virtual environment and also unsets `PYTHONPATH` for the run to avoid potential conflicts.

## Other Useful Makefile Commands

-   **`make setup`**: Sets up the Python virtual environment and installs dependencies (part of `make all`).
-   **`make build_whisper_cpp`**: Compiles `whisper.cpp` and downloads the model (part of `make all`).
-   **`make build_app`**: Builds only the `Kataru.app` bundle, assuming dependencies and `whisper.cpp` are already built (part of `make all`).
-   **`make clean`**: Removes all build artifacts, including the Python virtual environment (`.venv/`), `dist/` directory, PyInstaller's `build/` directory, and `whisper.cpp` build files. This is useful for a fresh start.

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

[microphones]
# Microphone preferences (substring matching, higher values = higher priority)
# The app will automatically select the best available device based on these preferences
seiren = 90
macbook = 80
sony = 70
headset = 60
airpods = 50
"携帯" = 5
teams = 1
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

### Python Environment Variable Conflicts when Running Manually
If you are trying to run `python3 dictate_app.py` manually (i.e., not using `make run_dev` or `make run`), and encounter issues like `ModuleNotFoundError: No module named 'encodings'`, it might be due to `PYTHONPATH` or `PYTHONHOME` environment variables pointing to incompatible Python environments.

The `make run_dev` command attempts to mitigate this by unsetting `PYTHONPATH` for its execution.

If running manually:
1.  Check for problematic variables:
    ```bash
    env | grep PYTHON
    ```
2.  If `PYTHONPATH` is set and causing issues, unset it for your current session:
    ```bash
    unset PYTHONPATH
    ```
    It's generally advisable to avoid having `PYTHONPATH` or `PYTHONHOME` set globally if you frequently work with different Python projects, as they can lead to unexpected behavior. Relying on virtual environments (which `make setup` and `make all` create) is usually a safer approach.

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

The application now includes intelligent microphone management:

**Automatic Device Selection:**
- The app automatically selects the best available microphone based on preferences defined in `config.ini`
- Microphone preferences use substring matching (e.g., "macbook" matches "MacBook Air Microphone")
- Higher priority values (1-100) indicate preferred devices
- The app monitors for device changes every 10 seconds and when the system wakes from sleep

**Manual Device Selection:**
If you need to troubleshoot audio issues or manually select a device:

1. Use the "List Audio Devices" menu option to see available devices with their priority scores
2. Use the "Change Audio Device" menu option to manually select a specific input device
3. Use "Refresh Audio Devices" if devices aren't appearing after connecting new hardware
4. The selected device index will be saved to `config.ini`

**Automatic Fallback:**
- If the selected microphone becomes unavailable (e.g., USB device unplugged), the app automatically switches to the next best available device
- The app handles sleep/wake cycles and device disconnections gracefully
- You'll see notifications when automatic device switching occurs

### Metal Support

For best performance, ensure Metal support is enabled when compiling whisper.cpp:
```bash
cmake -DGGML_METAL=ON ..
```

You should see Metal-related messages in the console output during transcription.

## License

[Specify your license here] 