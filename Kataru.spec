# -*- mode: python ; coding: utf-8 -*-
import os
import sys
import platform
from PyInstaller.utils.hooks import collect_data_files

# Ensure the project root is in sys.path for the spec file itself to find local modules
project_root_for_spec = os.path.abspath(".") # Use current working directory, which PyInstaller should set to project root
sys.path.insert(0, project_root_for_spec)

from version import __version__ # <-- Import the version

# --- Helper function to get relative path ---
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".") # Fallback for development

    return os.path.join(base_path, relative_path)

# --- Project Structure Assumptions ---
project_root = os.path.abspath(".")
whisper_cpp_dir = os.path.join(project_root, "whisper.cpp")
whisper_build_dir = os.path.join(whisper_cpp_dir, "build")
whisper_bin_dir = os.path.join(whisper_build_dir, "bin")
whisper_lib_dir = os.path.join(whisper_build_dir, "lib") # Assuming libs are in build/lib
whisper_model_dir = os.path.join(whisper_cpp_dir, "models")
assets_dir = os.path.join(project_root, "assets") # Path to the assets directory on disk

# --- App Icon Configuration ---
# IMPORTANT: The application icon 'kataru_app_icon.icns' should be in the 'assets' directory.
app_icon_source_on_disk = os.path.join(assets_dir, 'kataru_app_icon.icns')
app_icon_destination_folder_in_bundle = 'assets' # Icon will be in Contents/Resources/assets/
app_icon_filename_in_bundle = 'kataru_app_icon.icns'
# Path to the icon within the bundle, relative to Contents/Resources
final_icon_path_in_bundle = os.path.join(app_icon_destination_folder_in_bundle, app_icon_filename_in_bundle)

# --- Collect Data Files ---
# Format: (source_path, destination_within_bundle_resources)
datas = [
    ('config.ini', '.'), # config.ini in Contents/Resources
    (os.path.join(assets_dir, 'icon_default.png'), '.'), # Copy to root Resources, not assets subdir
    (os.path.join(assets_dir, 'icon_active.png'), '.'),  # Copy to root Resources, not assets subdir
    # Whisper executable (Copy to Resources/bin/)
    (os.path.join(whisper_bin_dir, 'whisper-cli'), 'bin'),
    # Whisper model (Copy to Resources/models/)
    (os.path.join(whisper_model_dir, 'ggml-small.en.bin'), 'models'),
    # Whisper libraries (Copy to Resources)
    (os.path.join(whisper_build_dir, 'ggml/src/libggml.dylib'), '.'),
    (os.path.join(whisper_build_dir, 'src/libwhisper.dylib'), '.'),
    (os.path.join(whisper_build_dir, 'ggml/src/libggml-base.dylib'), '.'),
    (os.path.join(whisper_build_dir, 'ggml/src/libggml-cpu.dylib'), '.'),
    # Add the application icon to data files
    (app_icon_source_on_disk, app_icon_destination_folder_in_bundle), 
]

# Add sounddevice library if PyInstaller doesn't find it automatically
# datas += collect_data_files('sounddevice')


# --- App Info.plist Settings ---
info_plist = {
    'CFBundleName': 'Kataru',
    'CFBundleDisplayName': 'Kataru',
    'CFBundleGetInfoString': "Kataru - Press-and-hold dictation",
    'CFBundleIdentifier': "com.codyroberts.kataru", # CHANGE THIS to your own unique ID
    'CFBundleVersion': __version__, # <-- Use imported version
    'CFBundleShortVersionString': __version__, # <-- Use imported version
    'NSHumanReadableCopyright': u"Copyright Kataru© 2024 Cody Roberts. All rights reserved.",
    'LSUIElement': True, # Make it an agent app (no Dock icon)
    'NSMicrophoneUsageDescription': 'Kataru requires microphone access to record audio for speech transcription.',
    'NSAppleEventsUsageDescription': 'Kataru requires permission to control System Events for pasting transcribed text.',
    'NSAccessibilityUsageDescription': 'Kataru requires accessibility permissions to detect the global hotkey press and release.',
}


a = Analysis(
    ['dictate_app.py'],
    pathex=[],
    binaries=[], # PyInstaller usually finds .dylibs, but we add whisper ones manually below if needed
    datas=datas, # Include our collected data files
    hiddenimports=['scipy.special._cdflib', 'PIL'], # Added PIL as it might be used by rumps or other libs for image handling
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Kataru', # The actual binary name inside MacOS folder
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False, # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None, # Auto-detect arch
    codesign_identity=None, # Set this to your Apple Developer ID for real signing
    entitlements_file=None, # Path to entitlements file if needed
)

# The old logic for creating icon_default.icns from icon_default.png is removed.
# The main app icon 'Kataru.icns' is now handled via the 'datas' list and 'icon' parameter in BUNDLE.

# COLLECT copies everything into the final app structure's Resources dir
# We add whisper dylibs to binaries here to potentially put them in Frameworks
coll = COLLECT(
    exe,
    a.binaries, # Includes automatically found binaries
    a.datas,    # Includes items specified in Analysis(datas=...)
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Kataru', # Temp build directory name
)

app = BUNDLE(
    coll,
    name='Kataru.app', # Final .app name
    icon=final_icon_path_in_bundle, # Use the defined path to the icon within the bundle
    bundle_identifier=info_plist['CFBundleIdentifier'],
    info_plist=info_plist, # Add our custom plist settings
    # codesign_identity="Developer ID Application: Cody Roberts (6L458UBN7J)", # Let script handle signing
    # entitlements_file='entitlements.plist' # Let script handle signing
)
