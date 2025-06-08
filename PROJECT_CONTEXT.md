# Project Context

This file tracks key information for the Kataru dictation project. 

## Environment

*   **Python:** System Python 3 or Homebrew Python 3.11+ recommended for development
*   **Virtual Environment:** `.venv` located at `/Users/codyroberts/software-design/speech-to-text/.venv`.
    *   Activation: `source .venv/bin/activate` 
    *   Creation: See "Environment Setup" section below

## Project Paths

*   **Project Directory:** `/Users/codyroberts/software-design/speech-to-text`
*   **Whisper.cpp Directory:** `/Users/codyroberts/software-design/speech-to-text/whisper.cpp`
*   **Whisper Model Path (small.en):** `/Users/codyroberts/software-design/speech-to-text/whisper.cpp/models/ggml-small.en.bin`

## Build Configuration

*   **Build System for whisper.cpp:** CMake. The `whisper.cpp` submodule is compiled using CMake.
*   **Project Build Orchestration:** The top-level `Makefile` in the project root orchestrates the entire build process, including `whisper.cpp` compilation and application bundling.
*   **Metal Support:** Enabled via CMake flag `-DGGML_METAL=ON` within the `Makefile` for `whisper.cpp` compilation.
*   **Main Executable Path (whisper-cli):** `/Users/codyroberts/software-design/speech-to-text/whisper.cpp/build/bin/whisper-cli` (This is created by the `Makefile`'s `build_whisper_cpp` or `all` targets).
*   **Stream Executable:** Not built by default (requires SDL2 library and `-DWHISPER_SDL2=ON` CMake flag).

## Script Configuration

*   **Hotkey:** F5 (`keyboard.Key.f5`) - Modified from original F6
*   **Audio Device Index:** Device indices are dynamic; use the app UI to list and select your microphone
*   **Configuration File:** `config.ini` (used for paths, audio settings, hotkey, icons)

## Environment Setup

The project supports two execution modes:

1. **Direct Script Execution (Development Mode)**
   * Requires proper environment setup to handle dependencies like PortAudio
   * Can be affected by Python environment variables set by previous py2app builds

2. **Bundled App Execution (Distribution Mode)**
   * Created via py2app, includes all dependencies and resources
   * Works independently from the development environment

To properly set up the development environment:

```bash
# The Makefile handles environment setup. For a full build including venv creation and dependencies:
make all

# To just setup the environment (create .venv and install requirements):
make setup
```

Key Makefile Targets:
* `make all`: Cleans previous app bundle, sets up the environment, builds `whisper.cpp`, downloads the model, and builds the `Kataru.app` bundle.
* `make setup`: Ensures the Python virtual environment (`.venv/`) is created and dependencies from `requirements.txt` are installed.
* `make build_whisper_cpp`: Compiles the `whisper.cpp` submodule and downloads the model.
* `make build_app`: Builds the `Kataru.app` bundle using PyInstaller (assumes environment and `whisper.cpp` are ready).
* `make run`: Runs the bundled `dist/Kataru.app`.
* `make run_dev`: Runs the application directly from `dictate_app.py` for development.
* `make clean`: Removes all build artifacts, including `.venv/`, `dist/`, `build/` (PyInstaller's), and `whisper.cpp/build/`.

## Key Architectural Improvements

* **PortAudio Detection:** The app now dynamically detects and pre-loads the PortAudio library in development mode, allowing direct script execution.
* **Environment Isolation:** Bundled and development modes are properly isolated to prevent conflicts.
* **Resource Path Handling:** All resource paths (model, icons, executable) are calculated based on execution context.
* **Error Handling:** Improved error messages and graceful fallbacks.
* **Intelligent Microphone Management:** Comprehensive device monitoring, preference-based selection, and automatic fallback logic.
* **Device Synchronization:** Maintains consistency between app state and microphone manager to prevent conflicts.
* **Sleep/Wake Event Handling:** Automatically refreshes device list when system wakes up to handle device changes.
* **Menu Management:** Enhanced microphone menu with proper clearing logic and rate limiting to prevent UI issues.

## Common Issues

### py2app Environment Variable Persistence

When running the app directly after building with py2app, you may encounter errors like:

```
ModuleNotFoundError: No module named 'encodings'
```

This happens because py2app sets environment variables that redirect Python to look for modules in the bundled app rather than standard locations:
- `PYTHONPATH=/Users/codyroberts/software-design/speech-to-text/dist/Kataru.app/Contents/Resources`
- `PYTHONHOME=/Users/codyroberts/software-design/speech-to-text/dist/Kataru.app/Contents/Resources`

The solution is to unset these variables:

```bash
unset PYTHONPATH
unset PYTHONHOME
unset PYTHONUNBUFFERED
unset PYTHONDONTWRITEBYTECODE
```

### Audio Device Selection & Troubleshooting

The application now includes intelligent device management that automatically handles most device-related issues:

**Normal Operation:**
- The app automatically selects the best microphone based on preferences in `config.ini`
- Device monitoring runs every 10 seconds and responds to sleep/wake events
- Automatic fallback occurs when devices become unavailable

**Troubleshooting Device Issues:**
If you encounter audio-related errors like:
```
PortAudioError starting recording: Error opening InputStream: Invalid number of channels
AudioHardware-mac-imp.cpp:660 AudioObjectGetPropertyData: no object with given ID XXX
```

**Immediate Solutions:**
1. Use "Refresh Audio Devices" menu option to force a device scan
2. Use "List Audio Devices" to see available devices with their priority scores  
3. Use "Change Audio Device" to manually select a different microphone
4. Check that your preferred device is connected and working in System Settings > Sound

**Configuration Solutions:**
1. Update microphone preferences in `config.ini` [microphones] section
2. Set higher priority values for reliable devices
3. Add new device patterns for devices you use regularly

**Advanced Troubleshooting:**
- The app automatically excludes failed devices when selecting alternatives
- Device synchronization issues are resolved automatically during device scans
- Sleep/wake cycles trigger immediate device refresh
- Retry logic prevents infinite loops when multiple devices fail

All device changes are automatically saved to `config.ini`, and the app provides notifications when automatic device switching occurs.

### Debugging Utility

The project includes a `test_microphones.py` utility script for troubleshooting microphone selection:

```bash
python3 test_microphones.py
```

This script shows:
- Available microphones and their device indices
- Configured preferences from `config.ini`
- Which microphone would be selected based on preferences
- Current `config.ini` device_index setting and its validity
- Preference scores for each available device

This is useful for debugging microphone selection issues or verifying that your preferences are configured correctly.

## Notes

*   **Using config.ini:** The `config.ini` file is used to store paths, audio settings, hotkey, and icons.
*   **Hotkey:** The hotkey for triggering the dictation process is F5 (changed from F6).
*   **Audio Device Index:** The default audio device index is 4, but can change. Use the UI to update it.
*   **Configuration File:** The `config.ini` file is used to store various settings and configurations for the project. 

## Audio Device Notes (Dynamic Indices & Intelligent Management)

*   **Device Enumeration:** The audio device indices are assigned dynamically by the operating system (Core Audio) and retrieved by `sounddevice`. They are **not fixed** and can change based on:
    *   Connecting or disconnecting audio devices (especially USB/Bluetooth).
    *   System restarts.
    *   Software updates affecting audio drivers.

*   **Intelligent Device Management:** The app now includes comprehensive microphone management:
    * **Automatic Device Selection:** Uses preference-based scoring defined in `config.ini` [microphones] section
    * **Continuous Monitoring:** Scans for device changes every 10 seconds and responds to sleep/wake events
    * **Smart Fallback Logic:** Automatically switches to alternative devices when the selected microphone becomes unavailable
    * **Device Synchronization:** Maintains sync between app state and microphone manager to prevent conflicts
    * **Menu Integration:** Microphone menu shows devices with priority scores and current selection indicator

*   **Device Selection Options:** The app provides multiple ways to manage microphone selection:
    * **Automatic (Recommended):** Configure preferences in `config.ini` and let the app choose the best available device
    * **Manual Selection:** Use "Change Audio Device" menu option to select a specific device
    * **Troubleshooting:** Use "List Audio Devices" to see all available devices with their priority scores
    * **Refresh:** Use "Refresh Audio Devices" to force a device scan after hardware changes

*   **Preference Configuration:** In `config.ini` [microphones] section, define substring patterns with priority values (1-100):
    ```ini
    [microphones]
    seiren = 90        # Matches "Razer Seiren Mini" 
    macbook = 80       # Matches "MacBook Air Microphone"
    sony = 70          # Matches Sony headsets
    headset = 60       # Generic headset match
    airpods = 50       # Matches AirPods devices
    "携帯" = 5         # Specific device name (quoted for special characters)
    teams = 1          # Microsoft Teams Audio (low priority)
    ```

*   **Error Handling & Recovery:** Enhanced error detection and recovery mechanisms:
    * Detects PortAudio errors including "Audio Hardware Not Running" and device ID conflicts
    * Implements retry logic with device exclusion to prevent infinite loops
    * Provides user notifications when automatic device switching occurs
    * Gracefully handles sleep/wake cycles and device disconnections

## macOS Permissions Issues

Properly configuring macOS permissions is crucial for Kataru to function correctly, especially when running as a bundled `.app`.

*   **`Info.plist` Usage Descriptions:** For the app to even request permissions, specific keys must be in the `Info.plist` file (managed by `Kataru.spec` for PyInstaller builds, or `setup.py` for `py2app`):
    *   `NSMicrophoneUsageDescription`: For recording audio. (e.g., "Kataru requires microphone access to record audio for speech transcription.")
    *   `NSAppleEventsUsageDescription`: For pasting text via AppleScript. (e.g., "Kataru requires permission to control System Events for pasting transcribed text.")
    *   `NSAccessibilityUsageDescription`: For global hotkey detection using `pynput`. (e.g., "Kataru requires accessibility permissions to detect the global hotkey press and release.")
    *   Without these, macOS may silently block access or not prompt the user.

*   **Granting Permissions in System Settings:** Even with `Info.plist` descriptions, users must grant permissions. The app *should* prompt automatically. If not, or if features are not working (e.g., hotkey unresponsive, no audio recorded, pasting fails), manually check and enable them in **System Settings > Privacy & Security**:
    *   **Microphone:** Ensure Kataru is listed and enabled.
    *   **Input Monitoring:** This is **essential** for the global hotkey (F5) to work. Kataru (or your terminal/Python if running in development mode directly) must be listed and enabled. If it's not listed, you may need to drag the `Kataru.app` bundle into the list or use the '+' button.
    *   **Accessibility:** `pynput` often requires this for robust global hotkey listening. Ensure Kataru is listed and enabled.
    *   **Automation:** For pasting to work, ensure Kataru is allowed to control "System Events" and/or other relevant applications.

*   **Troubleshooting Permission-Related Problems:**
    1.  **Quit Kataru Completely:** Ensure no instances are running.
    2.  **Check System Settings:** Go to Privacy & Security and verify each permission (Microphone, Input Monitoring, Accessibility, Automation).
    3.  **Toggle Permissions:** If Kataru is listed but disabled, enable it. If it's enabled but not working, try disabling it, then re-enabling it.
    4.  **Restart Kataru:** After making any changes in System Settings, restart the application.
    5.  **Re-add to List (Input Monitoring/Accessibility):** If toggling doesn't work, try removing Kataru from the Input Monitoring or Accessibility list (using the '-' button) and then re-adding it (using the '+' button and navigating to `dist/Kataru.app`).
    6.  **Console Logs:** Check the system Console.app for messages from `tccd` (Transparency, Consent, and Control daemon) related to Kataru, which might give clues about permission denials.
    7.  **Code Signing & Hardened Runtime:** As noted in "PyInstaller Bundling Notes", the Hardened Runtime can interfere with `pynput`. The `build_app.sh` script is configured to sign without the Hardened Runtime. If hotkeys fail specifically in bundled mode, ensure this signing process is completing correctly and no subsequent ad-hoc signing is re-enabling it or causing signature conflicts.

*   **Impact of Denied Permissions:**
    *   No Microphone access: App records silence or fails to start recording.
    *   No Input Monitoring/Accessibility: Global hotkey (F5) will not respond when Kataru is not the active application.
    *   No Automation: Pasting transcribed text will fail.

*   **Rebuilding (Legacy `py2app` Note):** The original notes mentioned rebuilding after `Info.plist` changes for `py2app`. For PyInstaller, changes to `Kataru.spec` (which defines the `Info.plist`) require a rebuild via `./build_app.sh`.

*   **Additional Troubleshooting (Legacy `py2app` Note):** The steps involving deleting the app, rebuilding with `-A`, and ad-hoc signing were specific to `py2app` debugging and may not be directly applicable or as effective for PyInstaller issues, which are more often tied to the `.spec` file, included `datas`, and the main signing step in `build_app.sh`.

## Visual Feedback and Hotkey Usage

*   **Menu Bar Icons:** The application provides visual feedback through changing menu bar icons:
    * Default icon (`icon_default.png`) is displayed when not recording
    * Active icon (`icon_active.png`) is displayed during recording
    * Icons revert to default upon errors or when recording stops
*   **Using the Hotkey:** 
    * Press and hold F5 (or configured key in config.ini) to begin recording
    * The menu bar icon changes to indicate recording is in progress
    * Release F5 when finished speaking to stop recording and begin transcription
    * Transcribed text is automatically pasted into the active application
*   **Customizing the Hotkey:** 
    * The hotkey can be changed in config.ini using the [Hotkey] key parameter
    * Supported formats include function keys (f1-f12), modifier keys (shift, ctrl, etc.), and single characters
    * Note that key combinations are not fully supported in the current version 

## py2app Bundling Notes & Troubleshooting (Summary of Debugging Session)

This section summarizes issues encountered and solutions found while bundling the application using `py2app`.

**1. Path Handling (Bundled vs. Script Mode):**
   - **Problem:** The app initially failed to find resources (config, model, executable, icons) when run as a bundled `.app` because it used paths relative to the script file (`__file__`) instead of the bundle's `Resources` directory.
   - **Solution:**
     - Detect bundle mode early in `__init__` using `is_bundled = hasattr(sys, 'frozen') and getattr(sys, 'frozen', False)`.
     - If `is_bundled`, calculate the `resource_dir` path: `os.path.normpath(os.path.join(os.path.dirname(sys.executable), "..", "Resources"))`.
     - **Crucially:** Calculate the `config_path` *first* based on the mode (`os.path.join(resource_dir, CONFIG_FILE)` if bundled, `os.path.join(BASE_DIR, CONFIG_FILE)` otherwise).
     - Read `config.ini` using the mode-specific `config_path`.
     - *After* reading the config, calculate all other paths (`main_exec_path`, `model_path`, `assets_dir`, `icon_default_path`, etc.) relative to `resource_dir` if bundled, or relative to `BASE_DIR` and config values (`whisper_cpp_dir`, `assets_dir`) if running as a script.
     - Ensure script-mode path calculation logic is strictly within the `else` block for `if is_bundled`. Do not let it run unconditionally and overwrite bundle paths.

**2. `setup.py` Configuration for `py2app`:**
   - **Problem (RecursionError):** The build process sometimes failed with `RecursionError` in `modulegraph`, likely due to complex/large dependencies being analyzed unnecessarily.
   - **Solution:** Add an `excludes` list to the `py2app` `OPTIONS` in `setup.py` to ignore irrelevant large packages. *Do not* exclude standard libraries needed by required packages (e.g., `unittest` was required by `numpy.testing`).
     ```python
     OPTIONS = {
         # ... other options ...
         'excludes': [
             'numpy.random._examples',
             'setuptools', 'pip', 'wheel', 'distutils',
             'pytest', 'test', 'tests',
             'torch', 'tensorflow', 'pandas', 'matplotlib'
         ],
     }
     ```
   - **Problem (PortAudio Library Not Found):** The bundled app crashed with `OSError: PortAudio library not found` or `ValueError: dylib ... could not be found` during the build.
   - **Solution:** Explicitly include the `libportaudio.dylib` using the `frameworks` option, pointing to the library *within the virtual environment's `sounddevice` installation*. Auto-discovery or system paths (`/usr/local/lib`) were unreliable.
     ```python
     OPTIONS = {
         # ... other options ...
         # Adjust python version/path as needed
         'frameworks': ['.venv/lib/python3.9/site-packages/_sounddevice_data/portaudio-binaries/libportaudio.dylib'],
     }
     ```
   - **Packages:** List direct Python dependencies in the `packages` option (e.g., `rumps`, `sounddevice`, `pynput`, `scipy`, `numpy`). Avoid adding overly complex packages here if they aren't direct imports, as it can trigger build analysis issues.
   - **Includes:** Explicitly add necessary modules, especially C extensions or platform-specific backends (e.g., `objc`, `cffi`, `_sounddevice`, `pynput.keyboard._darwin`).

**3. Threading and UI Updates (macOS/`rumps`):**
   - **Problem (`NSInternalInconsistencyException`):** Calling UI functions like `rumps.alert` from background threads (e.g., keyboard listener, transcription thread) crashed the app because UI updates must occur on the main thread.
   - **Solution:** Use `PyObjCTools.AppHelper.callAfter` to schedule the UI function call on the main event loop. Import it (`from PyObjCTools import AppHelper`) and use it in `except` blocks or any background thread needing UI interaction.
     ```python
     # Example in an except block:
     from PyObjCTools import AppHelper
     # ...
     except Exception as e:
         print(f"Error: {e}")
         AppHelper.callAfter(rumps.alert, title="Error Title", message=f"An error occurred: {e}")
     ```

**4. Debugging Bundled Apps Strategy:**
   - **Run from Terminal:** Always test builds by running the executable directly from the terminal (`./dist/AppName.app/Contents/MacOS/AppName`). This provides essential tracebacks and `print()` output hidden during normal Finder launch.
   - **Clean Builds:** Delete `build` and `dist` directories (`rm -rf build dist`) before rebuilding (`python3 setup.py py2app`) after making changes to `setup.py` or code affecting resource paths/imports.
   - **Logging/Prints:** Add detailed `print()` statements inside the `if is_bundled:` block and before critical steps (like `rumps.App` initialization) to verify paths and logic flow within the bundle.
   - **Console.app:** Use the macOS Console application to check for system-level errors or crash reports related to the app if terminal output isn't sufficient.
   - **File Permissions:** Verify execute permissions on included binaries within the bundle (`ls -l dist/AppName.app/Contents/Resources/your_executable`).

## PyInstaller Bundling Notes (Working Configuration)

After significant issues with `py2app`, the project was successfully bundled using **PyInstaller**.

**Key Configuration Points:**

1.  **Build Process:** The `Makefile` orchestrates the build (e.g., `make all` or `make build_app`).
    *   Activates/creates the `.venv` virtual environment.
    *   Installs dependencies from `requirements.txt`.
    *   Cleans previous PyInstaller `build/` and `dist/` directories before bundling.
    *   Builds the `whisper.cpp` libraries (via `make build_whisper_cpp` dependency).
    *   Runs `pyinstaller "Kataru.spec"` to build the app.
    *   The `build_app.sh` script (now removed) previously handled final code signing. This manual signing step might need to be re-integrated into the `Makefile` or post-build process if ad-hoc signing by PyInstaller is insufficient for distribution or causes issues.
2.  **Spec File (`Kataru.spec`):**
    *   Configures the `Analysis` step to include the main script (`dictate_app.py`) and necessary data files (`datas` list):
        *   `config.ini`
        *   Icon files (`assets/*.png`)
        *   `whisper-cli` executable (placed in `Resources/bin/`)
        *   Whisper model file (placed in `Resources/models/`)
        *   `whisper.cpp` `.dylib` files (placed directly in `Resources/`)
    *   Configures the `BUNDLE` step:
        *   Sets the application icon (`.icns`, auto-generated from `.png` if needed).
        *   Sets the `bundle_identifier`.
        *   Includes necessary `Info.plist` settings (permissions descriptions, `LSUIElement`).
        *   **Does NOT** specify `codesign_identity` or `entitlements_file` in the `.spec` itself, leaving final signing to be handled externally if needed.
3.  **Hardened Runtime:**
    *   The critical factor for allowing the F5 hotkey (via `pynput`) to work when the app is launched normally (`open ...`) was **disabling the Hardened Runtime** during the final code signing step (previously in `build_app.sh`).
    *   It appears the Hardened Runtime's restrictions interfere with the global event listener used by `pynput`.
    *   **Caution:** If distributing, investigate if a more targeted set of entitlements can be used with Hardened Runtime. For now, building without it is prioritized for functionality.
4.  **Dependencies:** `pyinstaller` is included in `requirements.txt`. `py2app` and `setup.py` have been removed.

**Outcome:** This configuration produces a working `.app` bundle in the `dist/` directory that launches correctly via `open` (or `make run`) and successfully handles hotkey listening, recording, transcription, and pasting.

### Maintaining Bundled App Compatibility

To prevent breaking the bundled `.app` version when updating the script or adding features, adhere to the following practices:

1.  **Understand Dual Execution Modes:** The application operates in two distinct modes:
    *   **Script Mode (Development):** Run via `make run_dev`. Paths are typically relative to the script file or project root, often guided by `config.ini`.
    *   **Bundled Mode (Distribution):** Run via `make run` or `open dist/Kataru.app`. Resources (executables, models, assets, dylibs) are located within the `.app/Contents/Resources/` directory. Path handling in `dictate_app.py` for this mode *must* reflect the structure defined by `Kataru.spec`.

2.  **`Kataru.spec` is the Authority for Bundle Structure:**
    *   The `datas` list in `Kataru.spec` dictates exactly where files are copied into `Contents/Resources/`.
    *   Any new data files (images, models, executables) needed by the bundled app *must* be added to this `datas` list with the correct source path and destination subfolder within `Resources`.

3.  **Python Code for Bundled Paths (`dictate_app.py`):**
    *   In `DictationApp.__init__`, the `if self.is_bundled:` block is critical for bundle-specific logic.
    *   Paths to bundled resources (e.g., `self.main_exec_path`, `self.model_path`, `self.assets_dir`) **must** be constructed directly relative to `self.resource_dir` (which points to `Contents/Resources/`).
    *   These constructed paths must exactly match the destinations specified in the `.spec` file (e.g., `os.path.join(self.resource_dir, 'bin', 'whisper-cli')`).
    *   **Avoid using `config.ini` settings like `whisper_cpp_dir` to form intermediate parts of critical resource paths when in bundled mode.** Their values are intended for script-mode's project structure.

4.  **Strategic `config.ini` Usage:**
    *   For file settings like `model_name` or icon names, `config.ini` should store only the base filename (e.g., `ggml-small.en.bin`). The Python code determines the directory based on execution mode.
    *   Settings like `whisper_cpp_dir` are primarily for script mode.
    *   Keep the `assets_dir` in `config.ini` as a simple relative name (e.g., `assets`); the Python code will resolve the full path.

5.  **Mandatory Dual Testing Protocol:**
    *   **After ANY code change potentially affecting paths, dependencies, or resource loading, BOTH modes MUST be tested:**
        1.  Test script mode: `make run_dev`
        2.  Rebuild the app: `make build_app` (or `make all` for a full rebuild from scratch after `make clean`)
        3.  Test bundled mode: `make run` or `open dist/Kataru.app`
    *   This is the single most important step to catch bundle-specific issues early.

6.  **Path Validation in `dictate_app.py`:**
    *   In `DictationApp.__init__`, after `self.main_exec_path`, `self.model_path`, etc., are defined, add `os.path.exists()` checks.
    *   If a critical file is not found, print a clear error message stating the execution mode (script/bundle), the full path that failed, and a troubleshooting hint (e.g., "Check .spec file or config.ini paths.").
    *   For bundled mode, consider using `rumps.alert` and `sys.exit()` if essential files like the model or executable are missing, to provide immediate user feedback.

7.  **Makefile Enhancements/Build Process:**
    *   The `make clean` target can be used for a full cleanup. `make all` effectively does a clean build of the app bundle by removing old `dist/` and PyInstaller's `build/` directories before bundling.
    *   The `Makefile`'s `build_whisper_cpp` target ensures `whisper.cpp` is compiled before the app bundle.
    *   **Consider adding a post-build verification step (to Makefile or script):** Could check for the existence of key files (e.g., `dist/Kataru.app/Contents/Resources/bin/whisper-cli`, `Resources/models/ggml-small.en.bin`) and fail the build if they are not found.

8.  **Dynamic Libraries (`.dylib`):**
    *   The `.spec` file correctly copies necessary `.dylib` files into `Contents/Resources/`.
    *   The Python code's practice of adding `self.resource_dir` to `DYLD_LIBRARY_PATH` in bundled mode is a good safeguard for `whisper-cli` finding its dependent libraries.

By following these guidelines, future development should be significantly less likely to break the bundled application. 