# Plan & Checklist: Custom Press-and-Hold Dictation App using Whisper on macOS

**Goal:** Develop a fast, accurate, and free voice-to-text application for macOS that implements a press-and-hold-to-dictate, release-to-transcribe-and-paste workflow.

**Hardware Target:** MacBook Air (Mac15,12) with Apple M3 Chip and 16GB RAM.

**Chosen Technology:** OpenAI Whisper model via the `whisper.cpp` implementation for optimized performance on Apple Silicon (leveraging Metal GPU acceleration).

**Chosen Application Approach:** Python script utilizing `pynput` for key listening, `sounddevice` for recording, and `osascript` for pasting.

---

## Progress Checklist

### Section 1: Prerequisites Installation

*   [X] **Install Xcode Command Line Tools:**
    *   Open `Terminal`.
    *   Run command: `xcode-select --install`
    *   Follow the on-screen prompts if they appear. Verify successful installation (usually indicated by a message or the command exiting without error after installation).
*   [X] **Install Homebrew:**
    *   Open `Terminal`.
    *   Run command: `/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"`
    *   Follow any instructions printed by the installer (e.g., adding Homebrew to PATH). Verify installation by running `brew --version`.
*   [X] **Install CMake:**
    *   Open `Terminal`.
    *   Run command: `brew install cmake`
    *   Verify installation by running `cmake --version`.
*   [X] **Create Python Virtual Environment:**
    *   Use system `python3`: `/usr/bin/python3 -m venv .venv`
    *   Activate: `source .venv/bin/activate` (Must be done in each new terminal session for the project).
*   [X] **Install Python Libraries (`pynput`, `sounddevice`, `numpy`, `scipy`) (Inside Activated Venv):**
    *   Ensure venv is active.
    *   Run command: `pip install pynput sounddevice numpy scipy`
    *   (Note: `numpy` and `scipy` are often dependencies for `sounddevice` or useful for audio handling; installing explicitly is safer).
*   [X] **Install `ffmpeg` (for audio conversion/handling if needed):**
    *   Open `Terminal`.
    *   Run command: `brew install ffmpeg`
    *   Verify installation by running `ffmpeg -version`.

---

### Section 2: Setup Whisper.cpp

*   [X] **Define Project Directory:**
    *   Choose a location for the project (e.g., `~/Developer`). Record the path: `PROJECT_DIR="~/Developer"` (Replace with actual path).
*   [X] **Clone `whisper.cpp` Repository:**
    *   Open `Terminal`.
    *   Run command: `cd "$PROJECT_DIR"`
    *   Run command: `git clone https://github.com/ggerganov/whisper.cpp.git`
    *   Record the path to the cloned repo: `WHISPER_CPP_DIR="$PROJECT_DIR/whisper.cpp"`
*   [X] **Navigate into Repository:**
    *   Open `Terminal`.
    *   Run command: `cd "$WHISPER_CPP_DIR"`
*   [X] **Download Whisper Model (`small.en`):**
    *   Ensure you are in the `$WHISPER_CPP_DIR` directory.
    *   Run command: `bash ./models/download-ggml-model.sh small.en`
    *   Verify the model file exists: `ls -l models/ggml-small.en.bin`
    *   Record model path: `MODEL_PATH="$WHISPER_CPP_DIR/models/ggml-small.en.bin"`
*   [X] **Compile `whisper.cpp` with Metal Support (using CMake):**
    *   Ensure you are in the `$WHISPER_CPP_DIR` directory.
    *   Run configuration command: `cmake -B build -DGGML_METAL=ON` *(Note: `-DWHISPER_METAL=ON` is deprecated)*
    *   Run build command: `cmake --build build -j --config Release`
    *   Verify executables exist: `ls -l build/bin/whisper-cli` *(Note: `stream`/`whisper-stream` is not built by default, requires SDL2)*
    *   Record main executable path: `MAIN_EXEC_PATH="$WHISPER_CPP_DIR/build/bin/whisper-cli"`
*   [X] **Initial Transcription Test (Manual):**
    *   [X] Record a short test audio file (e.g., using QuickTime Player or `ffmpeg`). Save as `test_audio.wav` in a known location (e.g., `$PROJECT_DIR/test_audio.wav`).
        *   Example recording command (requires `ffmpeg`, records 5 seconds): `ffmpeg -f avfoundation -i ":0" -t 5 "$PROJECT_DIR/test_audio.wav"`
    *   [X] Run transcription command from `$WHISPER_CPP_DIR`:
        ```bash
        "$MAIN_EXEC_PATH" -m "$MODEL_PATH" -f "$PROJECT_DIR/test_audio.wav" -otxt --no-timestamps
        ```
    *   [X] Confirm meaningful text output appears in the terminal.

---

### Section 3: Develop the Press-and-Hold Python Script

*   [X] **Create Script File:**
    *   Create a new file named `dictate_app.py` in `$PROJECT_DIR`.
*   [X] **Import Libraries:**
    *   Add imports to `dictate_app.py`: `import sounddevice as sd`, `import numpy as np`, `from pynput import keyboard`, `import subprocess`, `import tempfile`, `import os`, `import wave`, `from scipy.io.wavfile import write as write_wav`.
*   [X] **Define Constants:**
    *   Add constants in `dictate_app.py`:
        *   `WHISPER_CPP_DIR = "..."` (Use the actual path recorded earlier)
        *   `MAIN_EXEC_PATH = ".../whisper.cpp/build/bin/whisper-cli"` (Use the updated path)
        *   `MODEL_PATH = "..."` (Use the actual path recorded earlier)
        *   `HOTKEY = keyboard.Key.cmd_r` (Choose desired hotkey, e.g., Right Command. Adjust as needed)
        *   `SAMPLE_RATE = 16000` (Whisper prefers 16kHz)
        *   `CHANNELS = 1`
        *   `DEVICE_INDEX = 1` (Added based on ffmpeg output)
*   [X] **Implement Audio Recording Logic:**
    *   Create functions/logic to:
        *   Start recording audio using `sounddevice` when the hotkey is pressed down. Store frames in a list.
        *   Stop recording when the hotkey is released.
*   [X] **Implement Audio Saving Logic:**
    *   Upon stopping recording, save the captured audio frames to a temporary WAV file using `tempfile` and `wave` or `scipy.io.wavfile.write`. Ensure it's 16kHz mono PCM format. Record the temp file path.
*   [X] **Implement Transcription Logic:**
    *   Create a function that:
        *   Takes the temporary WAV file path as input.
        *   Constructs the `whisper.cpp` command string (e.g., `[MAIN_EXEC_PATH, "-m", MODEL_PATH, "-f", temp_wav_path, "-otxt", "--no-timestamps"]`).
        *   Uses `subprocess.run` to execute the command.
        *   Captures the `stdout` (transcribed text).
        *   Handles potential errors from the subprocess.
        *   Returns the transcribed text.
*   [X] **Implement Text Pasting Logic:**
    *   Create a function that:
        *   Takes the transcribed text as input.
        *   Constructs the `osascript` command to paste text (e.g., `osascript -e 'tell application "System Events" to keystroke "{escaped_text}"'`). Ensure text is properly escaped for shell and AppleScript.
        *   Uses `subprocess.run` to execute the `osascript` command.
        *   Handles potential errors.
*   [X] **Implement Keystroke Listener:**
    *   [X] Use `pynput.keyboard.Listener` to monitor global key presses and releases.
    *   [X] Define `on_press` and `on_release` handler functions.
    *   [X] In `on_press`, if the key matches `HOTKEY` and not already recording, start recording.
    *   [X] In `on_release`, if the key matches `HOTKEY` and currently recording:
        *   Stop recording.
        *   Save audio to temp file.
        *   Call transcription function.
        *   Call pasting function with the result.
        *   Clean up the temporary audio file (`os.remove`).
        *   Handle potential errors gracefully (e.g., print messages).
*   [X] **Implement Main Execution Block:**
    *   Add the `if __name__ == "__main__":` block.
    *   Initialize necessary state variables (e.g., `is_recording = False`, `audio_frames = []`). *(Handled by global scope)*
    *   Create and start the `pynput.keyboard.Listener`.
    *   Keep the script running (e.g., `listener.join()`).
    *   Include basic status messages (e.g., "Listening for hotkey...", "Recording started...", "Transcribing...", "Pasting..."). *(Added in main and functions)*
*   [X] **Initial Script Test (Execution):**
    *   Open `Terminal`.
    *   Run the script: `python3 "$PROJECT_DIR/dictate_app.py"`
    *   Press and hold the chosen hotkey, speak, then release.
    *   Verify text is pasted into the active application (e.g., TextEdit).
    *   Check terminal for status messages or errors.

---

### Section 4: Refinements (Optional but Recommended)

*   [X] **Refine Audio Recording Logic:** Implemented robust audio recording logic with error handling and state management.
*   [X] **Refine Transcription Logic:** Implemented robust transcription logic, including subprocess management, timeout, error handling, and removal of redundant file output (`-otxt`).
*   [X] **Refine Text Pasting Logic:** Implemented robust text pasting using `osascript` with error handling.
*   [X] **Refine Keystroke Listener:** Implemented robust keystroke listener using `pynput` within a thread, with error handling.
*   [X] **Refine Main Execution Block:** Refactored into a `rumps.App` class with initialization checks and graceful error handling.
*   [X] **Add Error Handling:** Improved robustness throughout (checked executable existence, handled empty recordings, managed subprocess errors, refined config loading, improved `sounddevice` errors).
*   [X] **Add Configuration:** Loaded settings (paths, hotkey, audio params, icons, whisper params) from `config.ini`.
*   [X] **Add Menu Bar Icon Feedback (using `rumps`):** Implemented status icons and basic menu items.
*   [X] **Add 'Edit Config' Menu Item:** Added functionality to open `config.ini`.
*   [X] **Hide Dock Icon (via App Bundling):** Added `LSUIElement=1` to `rumps` app info (will take effect fully when bundled).
*   [X] **Optimize Performance:** Tested models, enabled Metal, added configurable threads and timeout.
*   [X] **Refine Script Robustness & Performance:** Completed all sub-tasks (timeout, config loading, threads, sounddevice errors, removed `-otxt`).
*   [X] **Troubleshoot Bluetooth Audio:** Verified that audio device indices can change when Bluetooth headphones connect. Updated `config.ini` `device_index` to the correct value for the internal microphone (`3` in this case) while headphones were connected to resolve audio glitches and ensure the correct mic was used.
*   [/] **Implement Dynamic Microphone Selection and Fallback:** (Detailed implementation plan created in `reconciled_mic_implementation.md`)
    *   [ ] Create a mi crophone management system that:
        *   [ ] Scans for available input devices using `sounddevice.query_devices()` on every recording session.
        *   [ ] Implements a tiered/ranked preference system for microphone selection stored in `config.ini`.
        *   [ ] Automatically selects the highest-ranked available microphone from the preference list.
        *   [ ] Monitors for device connection/disconnection events (implement periodic re-scanning).
        *   [ ] Adds a notification system to inform users when microphone selection changes.
        *   [ ] Creates a menu item to display/select currently available microphones.
    *   [ ] Add a new section to the `config.ini` file for microphone preferences:
        ```
        [microphones]
        # Tiered microphone preferences - higher values = higher priority
        # Use partial or full device names as keys and priority as values
        # Example:
        # "Headset" = 100
        # "AirPods" = 90
        # "External Microphone" = 80
        # "Built-in" = 10
        # If no matches are found, will use first available input device
        ```
    *   [ ] Add functions to verify active microphone before recording starts.
    *   [ ] Implement graceful fallback to next available microphone if the current one becomes unavailable.
    *   [ ] Create a mechanism to handle a microphone disconnection during an active recording.
*   [ ] **Create Startup Mechanism:** Set up the script (or bundled app) to run automatically on login (e.g., using `launchd`).
*   [X] **Package as .app Bundle (Using PyInstaller):** *(Switched from py2app due to bundling issues)*
    *   [X] Install `PyInstaller` (`pip install pyinstaller`).
    *   [X] Configure PyInstaller (using `Kataru.spec`).
    *   [X] Include necessary `Info.plist` settings (`LSUIElement=1`, permissions) via `.spec` file.
    *   [X] Configure PyInstaller to include necessary data files (`config.ini`, icons, `whisper-cli`, `.gguf` model, `whisper.cpp` dylibs) via `.spec` file.
    *   [X] Build the `.app` bundle using `build_app.sh` (which runs `pyinstaller "Kataru.spec"`).
    *   [X] Test the standalone `.app` bundle.
    *   [X] Address path/dependency issues: Ensured correct data file destinations in `.spec`.
    *   [X] Address launch issues: Confirmed app works when Hardened Runtime is **disabled** during code signing (handled in `build_app.sh`). `pynput` listener likely incompatible with Hardened Runtime restrictions when app launched via `open`.

---

## Section 5: Maintaining Bundled App Compatibility and Testing

To ensure that development on the script version does not break the PyInstaller-bundled `.app`, the following practices are critical:

1.  **Acknowledge Dual Execution Contexts:**
    *   The application has two primary ways of running: directly via `python3 dictate_app.py` (or `./run_dictate_app.sh`) and as a bundled `.app` built by PyInstaller.
    *   Resource path handling (for `whisper-cli`, models, assets, dylibs) is the most significant difference and common source of errors between these modes.

2.  **The `.spec` File Governs Bundle Structure:**
    *   `Kataru.spec` is the definitive configuration for how PyInstaller packages the application.
    *   The `datas` list within the `.spec` file specifies which files are included in the bundle and their destination paths within `Contents/Resources/`.
    *   Any new resources required by the bundled app *must* be correctly added to this `datas` list.

3.  **Align Python Code with `.spec` for Bundled Mode:**
    *   In `dictate_app.py` (specifically in `DictationApp.__init__`), the `if self.is_bundled:` code block is responsible for setting up paths when running as a bundled app.
    *   Paths to resources like the `whisper-cli` executable, the model file, and assets directory **must** be constructed relative to `self.resource_dir` (which points to `Contents/Resources/`).
    *   These paths need to precisely match the destination structure defined in the `.spec` file's `datas` (e.g., if `.spec` places `whisper-cli` in `Resources/bin/`, Python must look for it there).
    *   **Crucially, avoid using `config.ini` values like `whisper_cpp_dir` to form parts of these critical resource paths when in bundled mode.** Such config settings are typically designed for the project layout during script-based development.

4.  **Strategic Use of `config.ini`:**
    *   For configurable filenames (e.g., `model_name`, icon filenames), store only the base filename in `config.ini`. The Python script should then prepend the correct directory path depending on whether it's running in script mode or bundled mode.
    *   The `whisper_cpp_dir` path in `config.ini` is primarily intended for script mode to locate the `whisper.cpp` build and model directories.
    *   Keep the `assets_dir` in `config.ini` as a simple relative name (e.g., `assets`); the Python script will resolve its full path based on the execution context.

5.  **Rigorous Dual-Mode Testing Protocol:**
    *   **This is the most vital step.** After any code modification that could impact file paths, resource loading, or external dependencies:
        1.  Thoroughly test the script mode: `./run_dictate_app.sh`.
        2.  Perform a clean rebuild of the application bundle: `./build_app.sh`.
        3.  Thoroughly test the bundled application: `open dist/Kataru.app`.
    *   Catching discrepancies early through this dual testing will save significant debugging time.

6.  **Implement Path Validation in Python:**
    *   Within `DictationApp.__init__`, after paths such as `self.main_exec_path` and `self.model_path` are determined, add `os.path.exists()` checks.
    *   If a required file is not found, log a detailed error message indicating:
        *   The execution mode (script or bundle).
        *   The full path that was checked and failed.
        *   A potential cause or suggestion (e.g., "Verify .spec file `datas` entry" or "Check `config.ini` path for script mode").
    *   For the bundled app, consider using `rumps.alert` and `sys.exit()` for critical missing files to provide immediate user feedback rather than a silent failure or crash.

7.  **Enhance Build Script (`build_app.sh`):**
    *   Always ensure the build script performs a clean build by removing previous `build/` and `dist/` directories (current script does this).
    *   **Consider adding automated post-build checks:** After PyInstaller finishes, the `build_app.sh` script could verify that essential files (e.g., `whisper-cli`, model file, key dylibs) exist at their expected locations

By consistently applying these development and testing practices, the integrity of both the script-based development version and the distributable bundled application can be maintained more effectively.

---

**Notes for Agent:**

---

**End of Plan**

