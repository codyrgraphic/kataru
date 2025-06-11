# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **DMG Creation System**: Implemented professional DMG installer creation using create-dmg
  - Added DMG creation targets to Makefile with version-aware naming (Kataru-{version}.dmg)
  - Integrated create-dmg tool for professional installer appearance with custom icons and layout
  - Added automatic staging directory management and cleanup
  - Created proper Applications symlink for drag-and-drop installation experience
  - DMG compression: 548MB app bundle → 464MB DMG file
- **User Documentation**: Created comprehensive setup and signing documentation
  - Added `assets/Privacy_Setup_Guide.txt` with clear setup instructions for users
  - Created `assets/SIGNING_NOTES.md` with code signing details and distribution status
  - Embedded privacy guide directly in DMG installer for user convenience
- **Permission Management**: Enhanced user experience with intelligent permission handling
  - Added "Check Permissions" menu item for real-time permission diagnosis
  - Implemented check_required_permissions() function to test Automation and Accessibility permissions
  - Enhanced error messages with specific guidance based on current permission status
  - Updated troubleshooting documentation to emphasize dual permission requirement

### Enhanced
- **Code Signing & Privacy Permissions**: Improved app security and user experience
  - Created Kataru.entitlements file with proper privacy permissions for microphone and speech recognition
  - Enhanced PyInstaller spec with improved privacy permission descriptions
  - Integrated automatic code signing with entitlements in build process
  - Added Developer ID Application certificate support with ad-hoc fallback
  - Updated privacy descriptions to emphasize local processing and data protection

### Changed
- **Build System Improvements**: Enhanced Makefile for professional distribution
  - Added DMG creation variables and targets with 5-stage progress feedback
  - Improved clean target to include DMG staging artifacts
  - Enhanced version extraction with fallback for robustness
  - Updated build process to include automatic code signing with entitlements
  - Optimized DMG layout with 800x450 window size and strategic icon placement

### Fixed
- **DMG Creation Issues**: Fixed Applications symlink conflict by letting create-dmg handle symlink creation
- **Build Process**: Enhanced error handling and progress feedback for large file DMG creation
- **CRITICAL Permission Flow**: Resolved confusing permission flow causing "Code 1" paste errors
  - Fixed misleading error messages that didn't explain dual permission requirement
  - Enhanced paste_text() function with intelligent permission checking
  - Added real-time permission diagnosis with specific guidance based on current status
  - Updated documentation to emphasize that BOTH Automation AND Accessibility permissions are required

### Technical Notes
- **Phase 1 & 2 Complete**: Foundation and Professional Polish phases implemented
- DMG creation time: ~1-2 minutes for large app bundles (548MB → 464MB)
- Code signing works seamlessly with Developer ID certificates
- All privacy permissions properly embedded and functional
- PyInstaller scipy warnings are non-critical for app functionality
- Professional DMG layout with privacy guide and optimized window sizing

## [0.1.3] - 2025-01-03

### Added
- Implemented automatic device monitoring with 10-second periodic scans to detect microphone changes
- Added sleep/wake event notifications to refresh device list when system wakes up
- Implemented intelligent microphone fallback logic that excludes failed devices when selecting alternatives
- Added retry counter mechanism to prevent infinite loops during device selection failures
- Added rate limiting (1-second) for microphone menu updates to prevent UI glitches
- Enhanced PortAudio error detection to catch "Audio Hardware Not Running" and "PaErrorCode -9986" errors
- Added preference-based microphone selection that automatically chooses the best available device on startup
- Implemented proper synchronization between app device index and microphone manager selection

### Changed
- Improved microphone menu clearing logic to use `clear()` method instead of faulty key-based iteration
- Enhanced device verification to check both cached availability and real-time sounddevice status
- Streamlined microphone selection to prioritize preference scores over config file device index
- Updated error handling to provide more specific fallback behavior for different PortAudio error types
- Refined device scanning to trigger automatic menu updates and device synchronization
- Improved startup initialization to properly sync microphone manager with app preferences

### Fixed
- **CRITICAL**: Fixed microphone menu showing duplicate entries - menu items now appear exactly once
- Resolved device synchronization issues where `mic_manager.current_mic_index` and `self.device_index` could become out of sync
- Fixed microphone selection not automatically switching to best available device when preferred device becomes unavailable
- Corrected device verification logic that was failing to detect stale device IDs after sleep/wake cycles
- Fixed menu update logic that was incorrectly trying to use dictionary methods on rumps MenuItem objects
- Resolved infinite recursion potential in start_recording when multiple devices fail consecutively

### Removed
- Removed excessive debug logging and verbose debugging statements throughout codebase
- Cleaned up temporary test files (`test_menu_fix.py`, `test_both_versions.py`) created during development
- Removed redundant debug comments (`[Debug]`, `[HotkeyDebug]`, `[IconDebug]`, `[AusE Debug]`)
- Streamlined code by removing unnecessary debug operations and verbose status messages

## [0.1.2] - YYYY-MM-DD

### Changed
- Refactored build and setup process using a `Makefile`, simplifying development and build workflows.
- Streamlined build scripts (`build_app.sh`, `setup_env.sh`) by removing redundant commands and commented-out legacy code.
- Refined `.gitignore` to include additional standard ignores (`.DS_Store`, `__pycache__/`, `app_output.log`).
- Cleaned up `dictate_app.py` by removing extensive commented-out code, unused variables, and obsolete comments/placeholders.
- Removed a duplicate entry in `australian_english_conversions.py`.
- Further standardized versioning to ensure `version.py` is the single source of truth.

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