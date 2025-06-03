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

*   **Build System:** CMake (Makefile is deprecated for compilation)
*   **Metal Support:** Enabled via CMake flag `-DGGML_METAL=ON` (Note: `-DWHISPER_METAL=ON` also worked but is deprecated).
*   **Main Executable Path:** `/Users/codyroberts/software-design/speech-to-text/whisper.cpp/build/bin/whisper-cli`
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
# If you have environment variables from previous py2app builds:
unset PYTHONPATH
unset PYTHONHOME
unset PYTHONUNBUFFERED
unset PYTHONDONTWRITEBYTECODE

# Create virtual environment (prefer Python 3.11+)
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Helper scripts:
* `run_dictate_app.sh` - Runs the app in development mode
* `setup_env.sh` - Sets up the virtual environment with dependencies
* `build_app.sh` - Builds the bundled app with py2app

## Key Architectural Improvements

* **PortAudio Detection:** The app now dynamically detects and pre-loads the PortAudio library in development mode, allowing direct script execution.
* **Environment Isolation:** Bundled and development modes are properly isolated to prevent conflicts.
* **Resource Path Handling:** All resource paths (model, icons, executable) are calculated based on execution context.
* **Error Handling:** Improved error messages and graceful fallbacks.

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

### Audio Device Selection

The application will automatically show audio devices in the menu. If an invalid device index is configured, you'll see errors when recording starts:

```
PortAudioError starting recording: Error opening InputStream: Invalid number of channels
```

Use the "List Audio Devices" menu option to see available devices, and "Change Audio Device" to select a new one. The change is automatically saved to `config.ini`.

## Notes

*   **Using config.ini:** The `config.ini` file is used to store paths, audio settings, hotkey, and icons.
*   **Hotkey:** The hotkey for triggering the dictation process is F5 (changed from F6).
*   **Audio Device Index:** The default audio device index is 4, but can change. Use the UI to update it.
*   **Configuration File:** The `config.ini` file is used to store various settings and configurations for the project. 

## Audio Device Notes (Dynamic Indices)

*   **Device Enumeration:** The audio device indices are assigned dynamically by the operating system (Core Audio) and retrieved by `sounddevice`. They are **not fixed** and can change based on:
    *   Connecting or disconnecting audio devices (especially USB/Bluetooth).
    *   System restarts.
    *   Software updates affecting audio drivers.
*   **Device Selection Solution:** The app includes "List Audio Devices" and "Change Audio Device" menu options to manage this issue more effectively:
    * "List Audio Devices" shows all available input devices and marks the currently selected one
    * "Change Audio Device" presents a dialog allowing users to select a new device by name
    * When a new device is selected, the config.ini file is automatically updated
    * This removes the need to manually check device indices or edit the config file

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

1.  **Build Script:** The `build_app.sh` script orchestrates the build.
    *   Activates the `.venv` virtual environment.
    *   Installs dependencies from `requirements.txt`.
    *   Cleans previous `build/` and `dist/` directories.
    *   Builds the `whisper.cpp` libraries.
    *   Runs `pyinstaller "Kataru.spec"` to build the app.
    *   Performs final code signing using a specific Developer ID (if configured in the script) **WITHOUT** the Hardened Runtime (`--options=runtime` is omitted from the `codesign` command).
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
        *   **Does NOT** specify `codesign_identity` or `entitlements_file`, leaving final signing to the build script.
3.  **Hardened Runtime:**
    *   The critical factor for allowing the F5 hotkey (via `pynput`) to work when the app is launched normally (`open ...`) was **disabling the Hardened Runtime** during the final code signing step in `build_app.sh`.
    *   It appears the Hardened Runtime's restrictions interfere with the global event listener used by `pynput`.
    *   **Caution:** Re-enabling Hardened Runtime (e.g., by adding `--options=runtime` back to `codesign` or using entitlements) may break hotkey functionality unless the exact required entitlements are identified and added.
4.  **Dependencies:** `pyinstaller` is included in `requirements.txt`. `py2app` and `setup.py` have been removed.

**Outcome:** This configuration produces a working `.app` bundle in the `dist/` directory that launches correctly via `open` and successfully handles hotkey listening, recording, transcription, and pasting.

### Maintaining Bundled App Compatibility

To prevent breaking the bundled `.app` version when updating the script or adding features, adhere to the following practices:

1.  **Understand Dual Execution Modes:** The application operates in two distinct modes:
    *   **Script Mode (Development):** Run via `./run_dictate_app.sh` or `python3 dictate_app.py`. Paths are typically relative to the script file or project root, often guided by `config.ini`.
    *   **Bundled Mode (Distribution):** Run via `open dist/Kataru.app`. Resources (executables, models, assets, dylibs) are located within the `.app/Contents/Resources/` directory. Path handling in `dictate_app.py` for this mode *must* reflect the structure defined by `Kataru.spec`.

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
        1.  Test script mode: `./run_dictate_app.sh`
        2.  Rebuild the app: `./build_app.sh` (which should perform a clean build)
        3.  Test bundled mode: `open dist/Kataru.app`
    *   This is the single most important step to catch bundle-specific issues early.

6.  **Path Validation in `dictate_app.py`:**
    *   In `DictationApp.__init__`, after `self.main_exec_path`, `self.model_path`, etc., are defined, add `os.path.exists()` checks.
    *   If a critical file is not found, print a clear error message stating the execution mode (script/bundle), the full path that failed, and a troubleshooting hint (e.g., "Check .spec file or config.ini paths.").
    *   For bundled mode, consider using `rumps.alert` and `sys.exit()` if essential files like the model or executable are missing, to provide immediate user feedback.

7.  **Build Script (`build_app.sh`) Enhancements:**
    *   Ensure the script always performs a clean build (deletes `build/` and `dist/` first).
    *   **Consider adding a post-build verification step:** The script could check for the existence of key files (e.g., `dist/Kataru.app/Contents/Resources/bin/whisper-cli`, `Resources/models/ggml-small.en.bin`) and fail the build if they are not found.

8.  **Dynamic Libraries (`.dylib`):**
    *   The `.spec` file correctly copies necessary `.dylib` files into `Contents/Resources/`.
    *   The Python code's practice of adding `self.resource_dir` to `DYLD_LIBRARY_PATH` in bundled mode is a good safeguard for `whisper-cli` finding its dependent libraries.

By following these guidelines, future development should be significantly less likely to break the bundled application. 