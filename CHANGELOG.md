# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
### Changed
- Refactored build and setup process using a `Makefile`, simplifying development and build workflows.
- Streamlined build scripts (`build_app.sh`, `setup_env.sh`) by removing redundant commands and commented-out legacy code.
- Refined `.gitignore` to include additional standard ignores (`.DS_Store`, `__pycache__/`, `app_output.log`).
- Cleaned up `dictate_app.py` by removing extensive commented-out code, unused variables, and obsolete comments/placeholders.
- Removed a duplicate entry in `australian_english_conversions.py`.
- Further standardized versioning to ensure `version.py` is the single source of truth.
### Fixed
### Removed
- Removed `setup_env.sh`, `build_app.sh`, and `run_dictate_app.sh` scripts, as their functionality is now handled by the `Makefile`.
- Legacy/redundant files from the repository:
  - `.DS_Store` (now gitignored)
  - `get-pip.py`
  - `implementation_steps.md`
  - `dynamic_mic_selection_implementation.md`
  - `reconciled_mic_implementation.md`
  - `test_audio.wav`, `test_audio_2.wav` (manual deletion by user)
  - `test_audio.wav.txt`, `test_audio_2.wav.txt`
- `app_version` key from `config.ini` (already noted in 0.1.1 but re-confirmed by recent cleanup).

## [0.1.1] - 2025-06-03

### Added
- Centralized version management using `version.py`.
- Created `CHANGELOG.md`.

### Changed
- Updated `Kataru.spec` and `dictate_app.py` (About dialog) to use `version.py` for version display.
- Updated `config.ini` (removed `app_version` as the About dialog now sources version from `version.py`).

### Fixed
- Resolved F5 hotkey issue in bundled app by ensuring correct code signing (no Hardened Runtime by default and removing conflicting ad-hoc signature).
- Reduced verbose logging for key presses in CLI mode.
- Updated documentation (`README.md`, `PROJECT_CONTEXT.md`, in-app troubleshooting) with detailed macOS permission instructions.

## [0.1.0] -2025-05-01

### Added
- Initial release of Kataru.
- Core features: Press-and-hold dictation (F5 default), menubar icon, Whisper.cpp integration, auto-paste.
- Configuration via `config.ini` for paths, hotkey, audio parameters, and Whisper settings.
- Bundled macOS application creation using PyInstaller (`Kataru.spec` and `build_app.sh`).
- Basic Australian English spelling conversion.
- Microphone selection and management UI, including listing and changing devices.
- Implemented fundamental audio recording (`sounddevice`), temporary WAV file saving, transcription (`whisper-cli` subprocess), and text pasting (`osascript`) workflow.
- Setup and integration of `whisper.cpp` compiled with Metal support for optimized performance.
- Python-based global keystroke listening (`pynput`) and audio handling (`sounddevice`).
- Visual feedback via menu bar icon changes (`rumps`) to indicate recording status.
- Initial error handling and configuration loading mechanisms.
- Support for running in both direct script execution (development) and bundled app modes with mode-dependent resource path handling.

### Changed
- Updated `Kataru.spec`