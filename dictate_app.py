#!/usr/bin/env python3

"""Press-and-hold voice dictation script using whisper.cpp and rumps menu bar icon."""

import configparser
import os
import subprocess
import tempfile
import threading
import time
import sys
import platform
import ctypes.util
from pathlib import Path
import re

# Import the conversion list
from australian_english_conversions import AUS_ENG_CONVERSIONS

# --- PortAudio Path Setup for Direct Execution ---
# This must happen before importing sounddevice
def setup_portaudio_path():
    """Configure paths to the PortAudio library for sounddevice.
    
    This allows running directly from the terminal with python3 dictate_app.py
    while preserving the bundled app functionality.
    """
    # Skip if we're running as a bundled app
    if hasattr(sys, 'frozen') and getattr(sys, 'frozen', False):
        print("Running as bundled app - skipping PortAudio path setup")
        return

    print("Running in direct execution mode - setting up PortAudio path")
    # Check for the typical sounddevice_data directory in the virtual environment
    base_dir = os.path.dirname(os.path.abspath(__file__))
    venv_path = os.path.join(base_dir, '.venv')
    
    # Determine Python version for the path (most likely 3.9 based on the project)
    py_version = '.'.join(platform.python_version_tuple()[:2])  # e.g., "3.9"
    
    # Construct potential paths to the libportaudio.dylib file
    potential_paths = [
        # Inside active venv
        os.path.join(venv_path, 'lib', f'python{py_version}', 'site-packages', 
                     '_sounddevice_data', 'portaudio-binaries', 'libportaudio.dylib'),
        # For system Python installs
        os.path.join(base_dir, '.venv', 'lib', f'python{py_version}', 'site-packages', 
                      '_sounddevice_data', 'portaudio-binaries', 'libportaudio.dylib'),
        # Check if it's in a standard system location
        '/usr/local/lib/libportaudio.dylib',
        # Add more potential paths if needed
    ]
    
    # Try to find a valid libportaudio.dylib path
    found_path = None
    for path in potential_paths:
        if os.path.exists(path):
            found_path = path
            break
    
    if found_path:
        print(f"Found PortAudio library at: {found_path}")
        # Add the directory to the dynamic library search path
        os.environ['DYLD_LIBRARY_PATH'] = os.path.dirname(found_path)
        # Directly load the library
        try:
            ctypes.CDLL(found_path)
            print("Successfully pre-loaded PortAudio library")
        except Exception as e:
            print(f"Warning: Failed to preload PortAudio library: {e}")
    else:
        print("Warning: Could not find PortAudio library. sounddevice import may fail.")

# Set up PortAudio paths before importing sounddevice
setup_portaudio_path()

import numpy as np
import rumps
import sounddevice as sd
from pynput import keyboard
from scipy.io.wavfile import write as write_wav
import objc
from PyObjCTools import AppHelper

# Import for sleep/wake notifications
import Cocoa
from Foundation import NSNotificationCenter, NSWorkspace

from version import __version__

# --- Constants from Config (Defaults) ---
# These will be overwritten by config file values
CONFIG_FILE = 'config.ini'
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Default values (used if config file is missing or incomplete)
DEFAULT_WHISPER_CPP_DIR = os.path.join(BASE_DIR, "whisper.cpp")
DEFAULT_MODEL_NAME = "ggml-small.en.bin"
DEFAULT_ASSETS_DIR = os.path.join(BASE_DIR, "assets")
DEFAULT_SAMPLE_RATE = 16000
DEFAULT_CHANNELS = 1
DEFAULT_DEVICE_INDEX = -1  # Use -1 for default input device
DEFAULT_HOTKEY_STR = "f6"
DEFAULT_ICON_DEFAULT = "icon_default.png"
DEFAULT_ICON_ACTIVE = "icon_active.png"
DEFAULT_TIMEOUT_SECONDS = 60  # Default transcription timeout
DEFAULT_NUM_THREADS = 4  # Default whisper threads

def parse_hotkey(key_str):
    """Parses a string from config into a pynput key object or combination."""
    # Simple key names (like 'f6', 'cmd_r', 'shift')
    if hasattr(keyboard.Key, key_str):
        return getattr(keyboard.Key, key_str)
    # Single characters
    elif len(key_str) == 1:
        return keyboard.KeyCode.from_char(key_str)
    # Combinations (like <ctrl>+<alt>+l) - Requires GlobalHotKeys (more complex)
    elif '+' in key_str and key_str.startswith('<') and key_str.endswith('>'):
        print(f"Warning: Hotkey combinations ({key_str}) are not fully supported. Using F6 as default.")
        return keyboard.Key.f6
    else:
        print(f"Warning: Unknown hotkey format: '{key_str}'. Using F6 as default.")
        return keyboard.Key.f6

class MicrophoneManager:
    """Manages microphone selection, preference tracking, and device changes."""
    
    def __init__(self, config, change_callback=None):
        """Initialize the microphone manager.
        
        Args:
            config: ConfigParser instance with microphone preferences
            change_callback: Function to call when the default microphone changes
        """
        self.preferences = self._load_preferences(config)
        self.available_mics = []
        self.current_mic_index = None
        self.change_callback = change_callback
        self.scan_timer = None
        self.scanning_interval = 5  # Seconds between device scans
        
    def _load_preferences(self, config):
        """Load microphone preferences from config."""
        preferences = {}
        if config.has_section('microphones'):
            for key, value in config.items('microphones'):
                try:
                    name = key.strip('"\\\'')  # Strip quotes if present
                    priority = int(value)
                    preferences[name.lower()] = priority
                except ValueError:
                    print(f"Warning: Invalid priority value for microphone {key}: {value}")
        return preferences
    
    def start_monitoring(self):
        """Start periodic scanning for device changes."""
        self.scan_devices()  # Initial scan 
            
    def stop_monitoring(self):
        """Stop monitoring for device changes."""
        if self.scan_timer:
            self.scan_timer.stop()
            self.scan_timer = None
    
    def scan_devices(self, _=None):  # Add _ for rumps.Timer compatibility
        """Scan for available microphones and update the available list."""
        try:
            devices = sd.query_devices()
            old_available_mic_indices_names = set((idx, name) for idx, name in self.available_mics)
            
            self.available_mics = []  # List of tuples: (index, name)
            
            for i, dev in enumerate(devices):
                if dev['max_input_channels'] > 0:
                    self.available_mics.append((i, dev['name']))

            current_mic_still_available = False
            if self.current_mic_index is not None:
                for idx, _ in self.available_mics:
                    if idx == self.current_mic_index:
                        current_mic_still_available = True
                        break
            
            if self.current_mic_index is not None and not current_mic_still_available:
                old_selected_index = self.current_mic_index
                print(f"Previously selected microphone (Index: {old_selected_index}, Name: {self.get_microphone_name(old_selected_index) if old_selected_index is not None else 'N/A'}) is no longer available.")
                self.current_mic_index = self.get_best_microphone_index()
                print(f"Switched to new best microphone (Index: {self.current_mic_index}, Name: {self.get_microphone_name(self.current_mic_index) if self.current_mic_index is not None else 'N/A'}).")
                if self.change_callback:
                    # Callbacks should ideally be thread-safe if they update UI
                    AppHelper.callAfter(self.change_callback, old_selected_index, self.current_mic_index)

            elif self.current_mic_index is None: # If no mic was selected, or if it became unavailable
                self.current_mic_index = self.get_best_microphone_index()
                print(f"No microphone was selected or previous became unavailable. Selected best: (Index: {self.current_mic_index}, Name: {self.get_microphone_name(self.current_mic_index) if self.current_mic_index is not None else 'N/A'})")
                # Trigger callback to notify the app of the new selection
                if self.change_callback and self.current_mic_index is not None:
                    AppHelper.callAfter(self.change_callback, None, self.current_mic_index)

            new_available_mic_indices_names = set((idx, name) for idx, name in self.available_mics)
            if old_available_mic_indices_names != new_available_mic_indices_names:
                print(f"Available microphones changed. New list: {self.available_mics}")
                # Potentially trigger a UI update if the list of mics shown in a menu changed,
                # even if the selected one didn't. This can be handled by the main app.
                if self.change_callback and self.current_mic_index is not None: # Check if a mic is selected
                     # Notify that list changed, selected mic might be the same or different
                    AppHelper.callAfter(self.change_callback, self.current_mic_index, self.current_mic_index, list_changed=True)

                
        except Exception as e:
            # Use AppHelper for alerts if this can be called from a non-main thread
            print(f"Error scanning audio devices: {e}")
            # AppHelper.callAfter(rumps.alert, title="Audio Device Error", message=f"Error scanning audio devices: {e}")
    
    def get_best_microphone_index(self, exclude_indices=None):
        """Get the index of the best available microphone based on preferences.
        
        Args:
            exclude_indices: List of device indices to exclude from selection
        """
        if exclude_indices is None:
            exclude_indices = []
            
        if not self.available_mics:
            print("Warning: No microphones available during best microphone selection.")
            return -1 # PortAudio default device index
            
        # Filter out excluded devices
        available_filtered = [(idx, name) for idx, name in self.available_mics if idx not in exclude_indices]
        
        if not available_filtered:
            print(f"Warning: No microphones available after excluding {exclude_indices}")
            return -1
            
        scored_mics = [] # List of (index, name, score)
        for idx, name in available_filtered:
            score = 0
            name_lower = name.lower()
            for pattern, priority in self.preferences.items():
                if pattern in name_lower: # Substring matching
                    score = max(score, priority)
            scored_mics.append((idx, name, score))
            
        scored_mics.sort(key=lambda x: x[2], reverse=True) # Sort by score descending
        
        if scored_mics and scored_mics[0][2] > 0: # If there's at least one match with preference
            excluded_note = f" (excluding {exclude_indices})" if exclude_indices else ""
            print(f"Best microphone selected based on preferences{excluded_note}: {scored_mics[0][1]} (Index: {scored_mics[0][0]}, Score: {scored_mics[0][2]})")
            return scored_mics[0][0]
        elif available_filtered: # No preference match, fallback to first available
            excluded_note = f" (excluding {exclude_indices})" if exclude_indices else ""
            print(f"No preference match{excluded_note}. Falling back to first available microphone: {available_filtered[0][1]} (Index: {available_filtered[0][0]})")
            return available_filtered[0][0]
        
        print("Warning: No microphones available and no preference match. Returning default device index.")
        return -1 # Default device as a last resort
    
    def get_microphone_name(self, index):
        """Get the name of a microphone by its index."""
        if index is None:
            return "None"
        for idx, name in self.available_mics:
            if idx == index:
                return name
        return f"Unknown Mic (Index {index})"
    
    def get_available_microphones(self):
        """Get list of available microphones with their scores (for menu display)."""
        scored_mics = []
        for idx, name in self.available_mics:
            score = 0
            name_lower = name.lower()
            for pattern, priority in self.preferences.items():
                if pattern in name_lower:
                    score = max(score, priority)
            scored_mics.append((idx, name, score))
        
        scored_mics.sort(key=lambda x: (x[2], x[1]), reverse=True) # Sort by score, then name
        return scored_mics
    
    def verify_microphone(self, index):
        """Verify if a microphone index is valid and available."""
        if index is None: 
            return False
        
        # Check if index is in our cached available list
        for idx, name in self.available_mics:
            if idx == index:
                # Additionally verify with sounddevice that the device still exists
                try:
                    devices = sd.query_devices()
                    if index < len(devices) and devices[index]['max_input_channels'] > 0:
                        return True
                    else:
                        return False
                except Exception as e:
                    print(f"Error checking device {index}: {e}")
                    return False
        
        return False

class DictationApp(rumps.App):
    # --- Class Level Info for macOS --- #
    # LSUIElement=1 hides the Dock icon, making it a background agent app
    info = {
        "LSUIElement": "1",
    }

   

    def _repl_func_factory(self, replacement_singular_text):
        def actual_repl_func(match_obj):
            original_token = match_obj.group(0)
            token_lower = original_token.lower()
            
            current_replacement = replacement_singular_text
            
            # Basic pluralization for the replacement if original was plural
            # and the replacement_singular_text is indeed singular.
            # This applies if the regex pattern matched a plural form (e.g. colors? matched "colors")
            # or if the matched word itself was an explicit plural that has a singular replacement defined.
            if token_lower.endswith('s') and not replacement_singular_text.lower().endswith('s'):
                # Avoid double pluralizing if original was like 'organisations' -> 'organisation'
                # This check ensures we only add 's' if the singular form would be appropriate.
                # This heuristic might need refinement for complex plurals.
                if replacement_singular_text.endswith('y') and len(replacement_singular_text) > 1 and replacement_singular_text[-2].lower() not in 'aeiou':
                     current_replacement = replacement_singular_text[:-1] + "ies"
                elif replacement_singular_text.endswith(('s', 'x', 'z', 'ch', 'sh')):
                     current_replacement = replacement_singular_text + "es"
                else:
                     current_replacement = replacement_singular_text + "s"
            
            # Case preservation
            if original_token.islower():
                return current_replacement.lower()
            if original_token.isupper():
                return current_replacement.upper()
            if original_token.istitle():
                # Ensure titlecasing works well for already cased AusE words
                return current_replacement[0].upper() + current_replacement[1:].lower() if current_replacement else ""

            # Mixed case (e.g. from a badly cased source, or if istitle() is not robust enough for all scenarios)
            # Simple approach: if original started with uppercase, replacement also starts with uppercase.
            if original_token and current_replacement: # Check not empty
                if original_token[0].isupper():
                    return current_replacement[0].upper() + current_replacement[1:].lower()
                else: # original starts lower
                    return current_replacement[0].lower() + current_replacement[1:].lower()
            return current_replacement # Fallback

        return actual_repl_func

    def convert_to_australian_english(self, text):
        if not text:
            return text, 0.0

        start_time = time.perf_counter()
        
        converted_text = text
        for pattern, aus_replacement_singular in AUS_ENG_CONVERSIONS:
            try:
                # Ensure pattern is treated as raw string if it contains backslashes for \b
                # The way AUS_ENG_CONVERSIONS is defined, patterns are already strings.
                # Python's r'' string literals are for defining them, not for re.sub call itself.
                # If \b is used, it must be '\\b' in a regular string or r'\b' in a raw string literal.
                # My list uses '\\b' so it should be fine.
                replacer = self._repl_func_factory(aus_replacement_singular)
                converted_text = re.sub(pattern, replacer, converted_text, flags=re.IGNORECASE)
            except re.error as e:
                print(f"Regex error for pattern '{pattern}': {e}")
                continue  # Skip faulty patterns

        end_time = time.perf_counter()
        conversion_time_ms = (end_time - start_time) * 1000
        return converted_text, conversion_time_ms

    def update_microphone_menu(self):
        """Update the microphone selection menu with current available microphones."""
        if not hasattr(self, 'mic_menu') or not hasattr(self, 'current_mic_indicator'):
            print("Microphone menu attributes not initialized yet. Skipping update.")
            return

        # Prevent excessive updates (rate limit to once per second)
        current_time = time.time()
        if hasattr(self, 'last_menu_update_time') and current_time - self.last_menu_update_time < 1.0:
            return
        
        self.last_menu_update_time = current_time
        
        # Clear existing microphone menu items
        self.mic_menu.clear()
        
        # Re-add the current microphone indicator at the top
        current_index = self.mic_manager.current_mic_index
        current_name = self.mic_manager.get_microphone_name(current_index)
        self.current_mic_indicator.title = f"Current: {current_name if current_name else 'None'}"
        self.mic_menu.add(self.current_mic_indicator)
        
        # Add a separator
        self.mic_menu.add(None)
        
        # Add available microphones to the menu
        available_mics = self.mic_manager.get_available_microphones()
        if not available_mics:
            no_mics_item = rumps.MenuItem("No microphones found")
            no_mics_item.set_callback(None)
            self.mic_menu.add(no_mics_item)
        else:
            for idx, name, score in available_mics:
                menu_title = f"{name} (Prio: {score})"
                if idx == current_index:
                    menu_title = f"▶ {menu_title}"  # Indicate current selection
                 
                menu_item = rumps.MenuItem(menu_title)
                menu_item.index = idx  # Store index for callback
                menu_item.set_callback(self.change_microphone_callback)
                self.mic_menu.add(menu_item)

    def change_microphone_callback(self, sender):
        """Callback for microphone menu items."""
        if not hasattr(sender, 'index'):
            print("Error: Menu item does not have an index attribute for change_microphone_callback")
            AppHelper.callAfter(rumps.alert, title="Menu Error", message="Could not change microphone due to an internal error (missing index).")
            return
        self.change_microphone(sender.index)

    def change_microphone(self, new_mic_index):
        """Change to a specific microphone."""
        if self.is_recording:
            AppHelper.callAfter(rumps.alert,
                title="Cannot Change Microphone",
                message="Cannot change microphone while recording is in progress."
            )
            return
        
        if not self.mic_manager.verify_microphone(new_mic_index):
            print(f"Attempted to switch to an invalid or unavailable microphone index: {new_mic_index}")
            AppHelper.callAfter(rumps.alert,
                title="Microphone Unavailable",
                message=f"The selected microphone (Index: {new_mic_index}) is no longer available or invalid."
            )
            # Refresh menu as a precaution
            AppHelper.callAfter(self.update_microphone_menu)
            return

        old_index = self.device_index # App's current device index
        old_name = self.mic_manager.get_microphone_name(old_index)
        
        # Update app's device_index and mic_manager's current_mic_index
        self.device_index = new_mic_index
        self.mic_manager.current_mic_index = new_mic_index
        new_name = self.mic_manager.get_microphone_name(new_mic_index)
        
        print(f"User manually changed microphone from '{old_name}' (Index: {old_index}) to '{new_name}' (Index: {new_mic_index})")
        
        # Update config file
        self.update_config_with_new_device()
        
        # Update UI (menu)
        # This will re-render the menu, showing the new selection as current
        AppHelper.callAfter(self.update_microphone_menu)
        
        # Notify user of manual change
        message = f"Microphone manually switched to: {new_name}"
        print(message)
        AppHelper.callAfter(rumps.notification,
            title="Microphone Changed",
            subtitle="User Selection",
            message=message
        )

    def update_config_with_new_device(self):
        """Update config.ini with the new device_index."""
        try:
            config = configparser.ConfigParser()
            # Read existing config to preserve other settings
            # Use self.config_path which is determined in __init__
            if not os.path.exists(self.config_path):
                print(f"Warning: Config file not found at {self.config_path} during update attempt.")
                # Optionally, create a default config here or simply return
                return 
                
            config.read(self.config_path)
            
            if not config.has_section('Audio'):
                config.add_section('Audio')
            config.set('Audio', 'device_index', str(self.device_index)) # device_index is the app's source of truth for config
            
            with open(self.config_path, 'w') as f:
                config.write(f)
            print(f"Updated config file ({self.config_path}) with new device index: {self.device_index}")
        except Exception as e:
            print(f"Error updating config file at {getattr(self, 'config_path', '[config_path_not_set]')}: {e}")
            AppHelper.callAfter(rumps.alert, title="Config Error", message=f"Could not save microphone selection to config file: {e}")

    def list_audio_devices(self, _=None):
        """Lists all available microphones with their priorities."""
        try:
            microphones = self.mic_manager.get_available_microphones()
            if not microphones:
                rumps.alert(title="No Microphones", message="No microphones available.")
                return
                
            device_info = []
            for idx, name, score in microphones:
                current_marker = ""
                if idx == self.device_index:
                    current_marker = " → CURRENT"
                device_info.append(f"{idx}: {name} (Priority: {score}){current_marker}")
                
            message = f"Available microphones:\n" + "\n".join(device_info)
            rumps.alert(title="Microphones", message=message)
            print(message)
        except Exception as e:
            print(f"Error listing microphones: {e}")
            AppHelper.callAfter(rumps.alert, title="Microphone Error", message=f"Error listing microphones: {e}")

    def __init__(self):
        # --- Determine if running as a bundled app *first* and store it --- #
        self.is_bundled = hasattr(sys, 'frozen') and getattr(sys, 'frozen', False)
        self.resource_dir = "" # Will be set if bundled

        super(DictationApp, self).__init__("", icon=None, quit_button="Quit Kataru")
        # rumps.notification(title="Kataru", subtitle="App is starting...", message="") # Removed startup notification

        # Initialize core attributes
        self.config = configparser.ConfigParser()
        self.config_path = "" # Determined based on mode (bundle/script)
        self.base_dir = BASE_DIR # Base directory of the script
        
        self.whisper_cpp_dir = DEFAULT_WHISPER_CPP_DIR
        self.model_name = DEFAULT_MODEL_NAME
        self.model_path = "" # Calculated after config load
        self.main_exec_path = "" # Calculated after config load
        self.assets_dir = DEFAULT_ASSETS_DIR
        self.icon_default_path = ""
        self.icon_active_path = ""
        self.menu_bar_icon_is_active = False

        self.sample_rate = DEFAULT_SAMPLE_RATE
        self.channels = DEFAULT_CHANNELS
        self.device_index = DEFAULT_DEVICE_INDEX  # Initial default before loading config
        self.audio_input_available = False  # Will be set by validation method
        self.transcription_timeout_seconds = DEFAULT_TIMEOUT_SECONDS
        self.num_threads = DEFAULT_NUM_THREADS

        self.recording_hotkey = parse_hotkey(DEFAULT_HOTKEY_STR)  # Initial default before config load
        self.is_recording = False
        self.recorded_data = []
        self.stream = None
        self.listener_thread = None  # For pynput listener
        self.timer_paused_by_recording = False  # Initialize the flag

        # Menu item instance for dynamic updates
        self.current_mic_indicator = rumps.MenuItem("Current: None")
        self.mic_menu = rumps.MenuItem("Microphones")  # Top-level menu item for microphone selection
        self.last_menu_update_time = 0  # Track last update to prevent excessive updates

        if self.is_bundled:
            # In bundled mode, resources are in Contents/Resources
            executable_path = os.path.dirname(sys.executable)
            self.resource_dir = os.path.normpath(os.path.join(executable_path, "..", "Resources"))
            self.config_path = os.path.join(self.resource_dir, CONFIG_FILE)
            print(f"Bundled mode: Resource directory set to {self.resource_dir}")
            print(f"Bundled mode: Config path set to {self.config_path}")
            
            # Set DYLD_LIBRARY_PATH for bundled .dylibs if needed by whisper-cli
            # This helps whisper-cli find .dylibs copied by PyInstaller into Resources
            dyld_library_path = os.environ.get('DYLD_LIBRARY_PATH', '')
            if self.resource_dir not in dyld_library_path:
                os.environ['DYLD_LIBRARY_PATH'] = f"{self.resource_dir}:{dyld_library_path}".strip(':')
                print(f"Bundled mode: Updated DYLD_LIBRARY_PATH: {os.environ['DYLD_LIBRARY_PATH']}")

        else: # Script mode
            self.config_path = os.path.join(self.base_dir, CONFIG_FILE)
            print(f"Script mode: Config path set to {self.config_path}")

        # Load configuration from config.ini
        self.load_config()  # This sets self.device_index, self.hotkey_str, etc.

        # Parse the actual hotkey from config
        self.recording_hotkey = parse_hotkey(self.hotkey_str)
        print(f"Recording hotkey: {self.recording_hotkey} (from '{self.hotkey_str}')")

        # Validate and set initial audio device after config is loaded
        self._validate_and_set_initial_audio_device()

        # Initialize MicrophoneManager after initial device validation
        self.mic_manager = MicrophoneManager(self.config, change_callback=self.on_microphone_changed)
        
        # Sync the mic_manager's current_mic_index with the app's device_index
        self.mic_manager.scan_devices()  # Initial scan to populate available_mics
        
        # Let mic_manager choose the best device based on preferences, then sync app to match
        best_mic_index = self.mic_manager.get_best_microphone_index()
        if best_mic_index != -1:
            # Check if the mic_manager's choice is different from config
            if best_mic_index != self.device_index:
                old_name = self.mic_manager.get_microphone_name(self.device_index)
                self.device_index = best_mic_index
                new_name = self.mic_manager.get_microphone_name(best_mic_index)
                print(f"Switching from '{old_name}' to '{new_name}' based on preferences")
                # Save the new device to config
                self.update_config_with_new_device()
            
            self.mic_manager.current_mic_index = best_mic_index
            print(f"Microphone synced: {self.mic_manager.get_microphone_name(best_mic_index)}")
        else:
            print("No valid microphones found during initialization")
            self.device_index = -1
            self.mic_manager.current_mic_index = -1

        # Paths that depend on config values (like whisper_cpp_dir) or bundle structure
        if self.is_bundled:
            # These paths MUST align with what's in Kataru.spec `datas`
            self.main_exec_path = os.path.join(self.resource_dir, "bin", "whisper-cli")
            self.model_path = os.path.join(self.resource_dir, "models", self.model_name)
            self.assets_dir = self.resource_dir # Assets are top-level in Resources if copied directly
            # If assets are in an 'assets' subdir within Resources (e.g. datas=[('assets', 'assets')])
            # self.assets_dir = os.path.join(self.resource_dir, "assets") 
        else: # Script mode
            self.main_exec_path = os.path.join(self.whisper_cpp_dir, "build", "bin", "whisper-cli")
            self.model_path = os.path.join(self.whisper_cpp_dir, "models", self.model_name)
            # self.assets_dir is already read from config or defaulted for script mode

        # Icon paths (must be resolved after assets_dir is known)
        self.icon_default_path = os.path.join(self.assets_dir, self.icon_default_name)
        self.icon_active_path = os.path.join(self.assets_dir, self.icon_active_name)
        
        # Set initial icon (ensure this is called after icon paths are resolved)
        self.set_menu_bar_icon(active=False)

        # Verify critical paths
        print(f"Path check - Main executable: {self.main_exec_path} (Exists: {os.path.exists(self.main_exec_path)})")
        print(f"Path check - Model: {self.model_path} (Exists: {os.path.exists(self.model_path)})")
        print(f"Path check - Default Icon: {self.icon_default_path} (Exists: {os.path.exists(self.icon_default_path)})")
        print(f"Path check - Active Icon: {self.icon_active_path} (Exists: {os.path.exists(self.icon_active_path)})")

        if not os.path.exists(self.main_exec_path):
            AppHelper.callAfter(rumps.alert, title="Error", message=f"Whisper CLI not found: {self.main_exec_path}")
        if not os.path.exists(self.model_path):
             AppHelper.callAfter(rumps.alert, title="Error", message=f"Whisper model not found: {self.model_path}")

        # Initialize the microphone submenu properly
        self.mic_menu.add(self.current_mic_indicator)
        self.mic_menu.add(None) # Separator
        
        # Define the initial structure of the menu. update_microphone_menu will populate self.mic_menu.submenu
        self.menu = [
            rumps.MenuItem("Start Dictation (Hold F5 then release)", callback=None), # Placeholder
            self.mic_menu, # Microphones submenu will be managed by update_microphone_menu
            rumps.MenuItem("Refresh Audio Devices", callback=self.manual_refresh_devices),
            None, # Separator
            rumps.MenuItem("Edit Config", callback=self.edit_config),
            rumps.MenuItem("Troubleshooting", callback=self.show_troubleshooting),
            rumps.MenuItem("About", callback=self.about)
        ]
        
        # Update microphone menu display initially and start monitoring
        self.update_microphone_menu() # Initial call to populate the menu
        self.mic_manager.start_monitoring() # Start after menu is somewhat set up

        # Create and start periodic device monitoring timer
        self.device_scan_interval = 10  # seconds - scan every 10 seconds
        self.device_monitor_timer = rumps.Timer(self.mic_manager.scan_devices, self.device_scan_interval)
        self.device_monitor_timer.start()
        print(f"Started periodic device monitoring every {self.device_scan_interval} seconds")

        # Register for sleep/wake notifications
        self.setup_system_event_notifications()

        # Start keyboard listener
        self.start_keyboard_listener()
        print("Kataru application initialized.")

    def set_menu_bar_icon(self, active):
        """Sets the menu bar icon to active or default.
        
        Args:
            active (bool): True to set active icon, False for default.
        """
        if active:
            if os.path.exists(self.icon_active_path):
                self.icon = self.icon_active_path
                self.menu_bar_icon_is_active = True
            else:
                print(f"Active icon not found at {self.icon_active_path}")
        else:
            if os.path.exists(self.icon_default_path):
                self.icon = self.icon_default_path
                self.menu_bar_icon_is_active = False
            else:
                print(f"Default icon not found at {self.icon_default_path}")

    def _validate_and_set_initial_audio_device(self):
        """
        Validates the configured audio device or selects a default one.
        Updates self.device_index and self.audio_input_available.
        Saves to config if a new device is selected.
        """
        self.audio_input_available = False # Assume unavailable until validated
        selected_device_info = "None" # For logging
        newly_selected_device = False # Initialize here, at the top of the method

        try:
            devices = sd.query_devices()
            # Filter for input devices (max_input_channels > 0)
            input_devices = [(i, dev) for i, dev in enumerate(devices) if dev['max_input_channels'] > 0]

            if not input_devices:
                print("CRITICAL: No input devices found by sounddevice.")
                # Defer UI alert to main thread
                AppHelper.callAfter(rumps.alert,
                                    title="Critical Audio Error",
                                    message="No microphones found on your system. Please connect a microphone. Recording will be disabled.")
                self.device_index = -1 # Ensure it's a non-specific value
                return

            current_device_is_valid_input = False
            if self.device_index != -1:  # A specific device is configured
                # Check if the configured device_index is in the list of valid input_devices
                for i, dev in input_devices:
                    if i == self.device_index:
                        current_device_is_valid_input = True
                        selected_device_info = f"'{dev['name']}' (Index {i})"
                        print(f"Initial check: Configured audio device {selected_device_info} is a valid input device.")
                        break
                if not current_device_is_valid_input:
                    print(f"Warning: Configured device_index {self.device_index} is invalid or not an input device. Attempting to select a new default.")
                    self.device_index = -1 # Force selection of a new default

            if self.device_index == -1: # Need to select a default (either initially or because configured was bad)
                print("Attempting to select a default audio input device.")
                # Try sounddevice\'s default input device
                try:
                    # sd.default.device is a list [input_idx, output_idx]
                    default_input_idx = sd.default.device[0]
                    if default_input_idx != -1: # If it's -1, sounddevice has no specific default input
                        for i, dev in input_devices: # Check if this default is in our list of valid inputs
                            if i == default_input_idx:
                                self.device_index = i
                                selected_device_info = f"'{dev['name']}' (Index {i})"
                                print(f"Using system default input device: {selected_device_info}")
                                current_device_is_valid_input = True
                                newly_selected_device = True
                                break
                        if not current_device_is_valid_input:
                             print(f"Warning: System default input index {default_input_idx} not found in available input devices or is not an input device. Will pick first available.")
                    else:
                        print("Sounddevice reports no specific default input device (index -1). Will pick first available.")
                except Exception as e_sdd:
                    print(f"Could not query sd.default.device: {e_sdd}. Will pick first available input device.")
                
                # If no system default was suitable or found, pick the first available input device
                if not current_device_is_valid_input and input_devices:
                    self.device_index, dev = input_devices[0] # Get index and device info
                    selected_device_info = f"'{dev['name']}' (Index {self.device_index})"
                    print(f"Selected first available input device: {selected_device_info}")
                    current_device_is_valid_input = True
                    newly_selected_device = True

            if current_device_is_valid_input:
                self.audio_input_available = True
                print(f"Final selected audio input device for startup: {selected_device_info}")
                # If we actively selected a new device (not just validated an existing one from config), save it.
                # Check if the device_index changed from what load_config provided or if it was initially -1
                # This check is a bit tricky here, so simpler: if newly_selected_device or initial was -1
                if newly_selected_device : # Check if logic path implies a change or confirmation of a default
                    print(f"Updating config with newly selected device_index: {self.device_index}")
                    # This should be safe from __init__ as it's on the main thread.
                    # If issues arise, wrap with AppHelper.callAfter(self.update_config_with_new_device)
                    self.update_config_with_new_device() 
            else:
                # This case should ideally not be reached if input_devices list was populated
                print("CRITICAL: Could not select any valid input device despite available devices being listed earlier.")
                AppHelper.callAfter(rumps.alert,
                                    title="Audio Setup Error",
                                    message="Could not automatically select a microphone. Please use 'Audio Settings > Change Audio Device' menu.")
                self.device_index = -1 # Fallback to non-specific

        except Exception as e_vad:
            print(f"FATAL: Error during initial audio device validation: {e_vad}", file=sys.stderr)
            AppHelper.callAfter(rumps.alert,
                                title="Fatal Audio Error",
                                message=f"Could not initialize audio system: {e_vad}. Please check audio hardware/drivers. Recording disabled.")
            self.device_index = -1 # Fallback
            self.audio_input_available = False # Ensure it's marked false
        
        print(f"Audio input available: {self.audio_input_available}, Device Index: {self.device_index}")

    def load_config(self):
        """Reads the configuration file from self.config_path."""
        self.config = configparser.ConfigParser()
        self._config_read_error = False # Initialize error flag for this load attempt
        
        print(f"Attempting to read configuration from {self.config_path}")
        found_configs = self.config.read(self.config_path, encoding='utf-8')

        if not found_configs:
            print(f"Warning: {CONFIG_FILE} not found at expected location: {self.config_path}. Using default settings.")
            # Set attributes directly if config is missing
            self.whisper_cpp_dir = DEFAULT_WHISPER_CPP_DIR
            self.model_name = DEFAULT_MODEL_NAME
            self.assets_dir = DEFAULT_ASSETS_DIR
            self.sample_rate = DEFAULT_SAMPLE_RATE
            self.channels = DEFAULT_CHANNELS
            self.device_index = DEFAULT_DEVICE_INDEX
            self.hotkey_str = DEFAULT_HOTKEY_STR
            self.icon_default_name = DEFAULT_ICON_DEFAULT
            self.icon_active_name = DEFAULT_ICON_ACTIVE
            self.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
            self.num_threads = DEFAULT_NUM_THREADS
        else:
            print(f"Successfully read configuration from {self.config_path}")
            # Read Paths
            self.whisper_cpp_dir = self.config.get('Paths', 'whisper_cpp_dir', fallback=DEFAULT_WHISPER_CPP_DIR)
            self.model_name = self.config.get('Paths', 'model_name', fallback=DEFAULT_MODEL_NAME)
            self.assets_dir = self.config.get('Paths', 'assets_dir', fallback=DEFAULT_ASSETS_DIR)

            # Read Audio (with error handling for int)
            try:
                self.sample_rate = self.config.getint('Audio', 'sample_rate', fallback=DEFAULT_SAMPLE_RATE)
            except ValueError:
                print(f"Warning: Invalid format for sample_rate in {CONFIG_FILE}. Using default: {DEFAULT_SAMPLE_RATE}")
                self.sample_rate = DEFAULT_SAMPLE_RATE
                self._config_read_error = True
            try:
                self.channels = self.config.getint('Audio', 'channels', fallback=DEFAULT_CHANNELS)
            except ValueError:
                print(f"Warning: Invalid format for channels in {CONFIG_FILE}. Using default: {DEFAULT_CHANNELS}")
                self.channels = DEFAULT_CHANNELS
                self._config_read_error = True
            try:
                self.device_index = self.config.getint('Audio', 'device_index', fallback=DEFAULT_DEVICE_INDEX)
            except ValueError:
                print(f"Warning: Invalid format for device_index in {CONFIG_FILE}. Using default: {DEFAULT_DEVICE_INDEX}")
                self.device_index = DEFAULT_DEVICE_INDEX
                self._config_read_error = True

            # Read Hotkey
            self.hotkey_str = self.config.get('Hotkey', 'key', fallback=DEFAULT_HOTKEY_STR)

            # Read Icons
            self.icon_default_name = self.config.get('Icons', 'icon_default', fallback=DEFAULT_ICON_DEFAULT)
            self.icon_active_name = self.config.get('Icons', 'icon_active', fallback=DEFAULT_ICON_ACTIVE)

            # Read Whisper settings (with error handling for int)
            try:
                self.timeout_seconds = self.config.getint('Whisper', 'timeout_seconds', fallback=DEFAULT_TIMEOUT_SECONDS)
            except (ValueError, configparser.NoSectionError):
                print(f"Warning: Invalid format or missing [Whisper] section for timeout_seconds in {CONFIG_FILE}. Using default: {DEFAULT_TIMEOUT_SECONDS}")
                self.timeout_seconds = DEFAULT_TIMEOUT_SECONDS
                if self.config.has_section('Whisper'): self._config_read_error = True
            try:
                self.num_threads = self.config.getint('Whisper', 'num_threads', fallback=DEFAULT_NUM_THREADS)
            except (ValueError, configparser.NoSectionError):
                print(f"Warning: Invalid format or missing [Whisper] section for num_threads in {CONFIG_FILE}. Using default: {DEFAULT_NUM_THREADS}")
                self.num_threads = DEFAULT_NUM_THREADS
                if self.config.has_section('Whisper'): self._config_read_error = True
                
    def start_keyboard_listener(self):
        """Starts the pynput keyboard listener in a separate thread."""
        if self.listener_thread is None or not self.listener_thread.is_alive():
            # Pass self to _run_listener if it needs access to DictationApp attributes directly
            self.listener_thread = threading.Thread(target=self._run_listener, daemon=True)
            self.listener_thread.start()
            print("Keyboard listener thread started.")
        else:
            print("Keyboard listener thread already running.")

    @rumps.clicked("Edit Config")
    def edit_config(self, sender):
        """Opens the config.ini file in the default text editor."""
        # Determine if running as a bundled app
        is_bundled = hasattr(sys, 'frozen') and getattr(sys, 'frozen', False)
        
        if is_bundled:
            # Get the resource directory path for bundled app
            executable_dir = os.path.dirname(sys.executable)
            resource_dir = os.path.normpath(os.path.join(executable_dir, "..", "Resources"))
            config_path = os.path.join(resource_dir, CONFIG_FILE)
        else:
            # Use BASE_DIR for direct execution
            config_path = os.path.join(BASE_DIR, CONFIG_FILE)
            
        print(f"Attempting to open config file: {config_path}")
        try:
            # Use subprocess.run for better error handling than os.system
            result = subprocess.run(["open", config_path], check=False, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error opening config file: {result.stderr}")
                rumps.alert(title="Config Error", message=f"Could not open {CONFIG_FILE}:\n{result.stderr}")
            else:
                print("Config file opened successfully.")
        except Exception as e:
            print(f"Exception opening config file: {e}")
            rumps.alert(title="Config Error", message=f"Could not open {CONFIG_FILE}:\n{e}")

    def _run_listener(self):
        """Runs the pynput keyboard listener in a separate thread."""
        print("Keyboard listener thread started.")
        try:
            # Define handlers within the scope where self is accessible
            def on_press(key):
                self.on_press(key)
            def on_release(key):
                self.on_release(key)

            # Start the listener
            with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
                self.listener_thread = listener # Store reference
                listener.join() # Keep the thread running
        except Exception as e:
            err_msg = f"Error in keyboard listener: {e}"
            print(err_msg)
            AppHelper.callAfter(rumps.alert, title="Listener Error", message=err_msg) # Use callAfter
            # Optionally, try to signal the main thread to quit if listener dies

    # --- Audio Handling ---
    def audio_callback(self, indata, frames, time, status):
        if status:
            print(f"Audio callback status: {status}", file=sys.stderr)
        # Ensure recording is supposed to be active
        if self.is_recording: # Remove the thread ID check
            self.recorded_data.append(indata.copy())



    def start_recording(self, retry_count=0):
        if self.is_recording:
            print("Already recording.")
            return

        # Prevent infinite retry loops
        MAX_RETRIES = 2
        if retry_count >= MAX_RETRIES:
            print(f"Max retries ({MAX_RETRIES}) exceeded for start_recording, aborting.")
            AppHelper.callAfter(rumps.alert, 
                title="Recording Failed", 
                message="Unable to start recording after multiple attempts. Please check your microphone connections and try manually selecting a different device.")
            return

        # Ensure mic_manager is available
        if not hasattr(self, 'mic_manager'):
            print("Error: MicrophoneManager not initialized. Cannot start recording.")
            AppHelper.callAfter(rumps.alert, title="Startup Error", message="Microphone manager failed to load. Please restart.")
            return

        # Force a device scan before attempting to record to catch stale device IDs
        self.mic_manager.scan_devices()
        
        # Verify the current microphone (self.device_index) is still available via mic_manager
        # The app's self.device_index should be kept in sync with mic_manager.current_mic_index
        if not self.mic_manager.verify_microphone(self.device_index):
            print(f"Selected microphone (Index: {self.device_index}, Name: {self.mic_manager.get_microphone_name(self.device_index)}) is no longer available.")
            old_unavailable_index = self.device_index
            old_unavailable_name = self.mic_manager.get_microphone_name(old_unavailable_index)
            
            # Attempt to switch to the best available microphone determined by mic_manager
            new_best_index = self.mic_manager.get_best_microphone_index()
            
            if new_best_index == -1: # No mics available at all
                message = f"Microphone '{old_unavailable_name}' is unavailable, and no other microphones were found. Recording cannot start."
                print(message)
                AppHelper.callAfter(rumps.alert, title="Microphone Error", message=message)
                self.set_menu_bar_icon(active=False)
                return

            self.device_index = new_best_index
            self.mic_manager.current_mic_index = new_best_index  # Keep mic_manager in sync
            new_name = self.mic_manager.get_microphone_name(self.device_index)
            
            print(f"Automatically switched from unavailable '{old_unavailable_name}' to '{new_name}' (Index: {self.device_index})")
            
            # Update config and UI to reflect this automatic change
            self.update_config_with_new_device()
            AppHelper.callAfter(self.update_microphone_menu)  # Update menu on main thread
            
            message = f"Mic '{old_unavailable_name}' was unavailable. Switched to '{new_name}'."
            AppHelper.callAfter(rumps.notification,
                title="Microphone Auto-Switched",
                subtitle="Recording started",
                message=message
            )
        else:
            # Mic is available, print confirmation
            print(f"Verified current microphone before recording: {self.mic_manager.get_microphone_name(self.device_index)} (Index: {self.device_index})")

        # Continue with existing recording logic using self.device_index
        print(f"Attempting to start recording with: {self.mic_manager.get_microphone_name(self.device_index)} (Index: {self.device_index})")
        self.set_menu_bar_icon(active=True)
        self.audio_frames = []
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.audio_callback,
                device=self.device_index # Use the (potentially updated) self.device_index
            )
            self.stream.start()
            self.is_recording = True
            print(f"Recording started successfully with: {self.mic_manager.get_microphone_name(self.device_index)} (Index: {self.device_index})")
        except sd.PortAudioError as pae:
            print(f"PortAudioError starting recording on device {self.device_index} ({self.mic_manager.get_microphone_name(self.device_index)}): {pae}")
            self.set_menu_bar_icon(active=False)
            self.is_recording = False  # Ensure is_recording is reset
            self._close_stream_safely()
            
            # More detailed PortAudioError handling
            original_failed_device_index = self.device_index
            original_failed_device_name = self.mic_manager.get_microphone_name(original_failed_device_index)

            # If error is related to the device, try fallback (even if verify_microphone passed initially, something else could go wrong)
            if ("Invalid device" in str(pae) or "Device unavailable" in str(pae) or 
                "Invalid number of channels" in str(pae) or "Unanticipated host error" in str(pae) or
                "Audio Hardware Not Running" in str(pae) or "PaErrorCode -9986" in str(pae)):
                print(f"PortAudioError suggests device '{original_failed_device_name}' (Index {original_failed_device_index}) is problematic. Attempting fallback.")
                # Ask mic_manager for the next best option that ISN'T the one that just failed
                # This requires a temporary modification to preferences or a new mic_manager method, 
                # or simply get_best_microphone_index and hope it picks a different one if the list updated.
                # For simplicity, we'll re-scan and get best. If it's the same, the error is likely persistent.
                
                self.mic_manager.scan_devices() # Re-scan to ensure list is fresh
                new_fallback_index = self.mic_manager.get_best_microphone_index(exclude_indices=[original_failed_device_index])

                if new_fallback_index != -1:
                    self.device_index = new_fallback_index
                    self.mic_manager.current_mic_index = new_fallback_index # Sync mic_manager
                    new_fallback_name = self.mic_manager.get_microphone_name(new_fallback_index)

                    message = f"Audio device '{original_failed_device_name}' failed. Trying '{new_fallback_name}'..."
                    print(message)
                    AppHelper.callAfter(rumps.notification,
                        title="Microphone Error - Retrying",
                        subtitle="Attempting fallback",
                        message=message
                    )
                    self.update_config_with_new_device()
                    AppHelper.callAfter(self.update_microphone_menu)
                    
                    # Retry start_recording with retry counter to prevent infinite loops
                    print(f"Retrying start_recording with the new fallback device (attempt {retry_count + 1}).")
                    self.start_recording(retry_count + 1)  # Recursive call with retry counter
                    return  # Exit current failed attempt
                else:  # new_fallback_index is -1 (no alternative devices found)
                    print(f"Fallback attempt failed: No alternative microphones found after excluding failed device {original_failed_device_index}")
                    # Fall through to generic error message
            
            # Generic error message if no specific fallback occurred or fallback also failed
            msg = f"Could not start audio recording with {original_failed_device_name} (PortAudio Error):\n{pae}\n\nThis often happens after sleep/wake or logout/login. Try:\n1. Use 'Change Audio Device' to select a different microphone\n2. Restart Kataru\n\nTechnical details: Device ID {original_failed_device_index} became invalid."
            AppHelper.callAfter(rumps.alert, title="Audio Recording Error", message=msg)

        except Exception as e:
            print(f"Generic error starting recording on device {self.device_index} ({self.mic_manager.get_microphone_name(self.device_index)}): {e}")
            self.set_menu_bar_icon(active=False)
            self.is_recording = False # Ensure is_recording is reset
            self._close_stream_safely()
            msg = f"Could not start audio recording with {self.mic_manager.get_microphone_name(self.device_index)}:\n{e}"
            AppHelper.callAfter(rumps.alert, title="Recording Error", message=msg)

    def _close_stream_safely(self):
        """Helper method to safely close the audio stream."""
        if self.stream:
            try:
                self.stream.close()
                print("Closed stream after error.")
            except Exception as e_close:
                print(f"Exception closing stream after error: {e_close}")
            finally:
                self.stream = None

    def stop_recording(self):
        """Stop recording and return the recorded audio data."""
        if not self.is_recording:
            print("Not currently recording.")
            return None
            
        print("Stopping recording...")
        self.is_recording = False
        
        # Stop and close the audio stream
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
                print("Audio stream stopped and closed.")
            except Exception as e:
                print(f"Error stopping audio stream: {e}")
            finally:
                self.stream = None
        
        # Set icon back to default
        self.set_menu_bar_icon(active=False)
        
        # Process recorded data
        if not self.recorded_data:
            print("No audio data recorded.")
            return None
            
        try:
            # Concatenate all recorded chunks into a single array
            recording = np.concatenate(self.recorded_data, axis=0)
            print(f"Recording stopped. Total samples: {len(recording)}, Duration: {len(recording) / self.sample_rate:.2f} seconds")
            
            # Clear recorded data for next recording
            self.recorded_data = []
            
            return recording
        except Exception as e:
            print(f"Error processing recorded data: {e}")
            self.recorded_data = []  # Clear even on error
            return None

    # --- File Saving ---
    def save_audio_to_temp_file(self, recording):
        if recording is None or recording.size == 0: print("Recording data is empty, cannot save."); return None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_wav_path = tmp_file.name
                print(f"Saving audio to: {temp_wav_path}")
                if recording.dtype == np.float32 or recording.dtype == np.float64:
                    recording_int16 = np.int16(recording * 32767)
                elif recording.dtype == np.int16:
                    recording_int16 = recording
                else:
                    print(f"Unsupported dtype: {recording.dtype}. Attempting conversion.")
                    recording_int16 = np.int16(recording * 32767 if np.issubdtype(recording.dtype, np.floating) else recording)
                write_wav(temp_wav_path, self.sample_rate, recording_int16)
                print(f"Successfully saved to {temp_wav_path}")
                return temp_wav_path
        except Exception as e:
            print(f"Error saving audio: {e}")
            # This might be called from different threads, use callAfter
            AppHelper.callAfter(rumps.alert, title="Save Error", message=f"Could not save audio: {e}")
            return None

    # --- Transcription ---
    def transcribe_audio(self, file_path):
        if not file_path or not os.path.exists(file_path): print(f"Transcription error: File not found: {file_path}"); return None
        print(f"Transcribing: {file_path} (Timeout: {self.timeout_seconds}s, Threads: {self.num_threads})")
        command = [
            self.main_exec_path,
            "-m", self.model_path,
            "-f", file_path,
            "-t", str(self.num_threads),
            "--no-timestamps"
        ]
        transcribed_text = None
        try:
            process = subprocess.run(
                command,
                capture_output=True, text=True, check=True,
                timeout=self.timeout_seconds
            )
            transcribed_text = process.stdout.strip()
            if not transcribed_text:
                print("Transcription empty (stdout).")
                return None
            print(f"Transcription successful: {transcribed_text[:100]}...")
            return transcribed_text
        except FileNotFoundError:
            print(f"Error: whisper.cpp exec not found at {self.main_exec_path}")
            msg = f"Whisper exec not found:\n{self.main_exec_path}"
            AppHelper.callAfter(rumps.alert, title="Exec Error", message=msg) # Use callAfter
            return None
        except subprocess.TimeoutExpired:
            print(f"Error: Transcription subprocess timed out after {self.timeout_seconds} seconds.")
            msg = f"Transcription took longer than {self.timeout_seconds}s."
            AppHelper.callAfter(rumps.alert, title="Transcription Timeout", message=msg) # Use callAfter
            return None
        except subprocess.CalledProcessError as e:
            # Stderr is already included in the exception details printed here
            print(f"Whisper Error (Code {e.returncode}):\nStderr: {e.stderr}\nStdout: {e.stdout}")
            msg = f"Whisper Error (Code {e.returncode}):\n{e.stderr[:200]}..."
            AppHelper.callAfter(rumps.alert, title="Transcription Error", message=msg) # Use callAfter
            return None
        except Exception as e:
            print(f"Unexpected transcription error: {e}")
            msg = f"Unexpected error: {e}"
            AppHelper.callAfter(rumps.alert, title="Transcription Error", message=msg) # Use callAfter
            return None
        # Ensure we return None if an exception occurred above
        return transcribed_text # This line is reached only on success

    # --- Pasting Text ---
    def paste_text(self, text_to_paste):
        if not text_to_paste: print("No text to paste."); return
        print(f"Pasting: {text_to_paste[:100]}...")

        # --- Reverted to osascript Implementation --- #
        escaped_text = text_to_paste.replace('\\', '\\\\').replace('"', '\\"')
        applescript_command = f'set the clipboard to "{escaped_text}"\ndelay 0.1\ntell application "System Events" to keystroke "v" using command down'
        command = ["osascript", "-e", applescript_command]
        try:
            process = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
            print("Paste success via osascript.")
            if process.stdout: print(f"osascript stdout: {process.stdout.strip()}")
            if process.stderr: print(f"osascript stderr: {process.stderr.strip()}")
        except FileNotFoundError:
            print("Error: 'osascript' command not found.")
            msg = "osascript command not found."
            AppHelper.callAfter(rumps.alert, title="Paste Error", message=msg) # Use callAfter
        except subprocess.TimeoutExpired:
             print("Error: osascript paste command timed out.")
             msg = "Paste command timed out."
             AppHelper.callAfter(rumps.alert, title="Paste Error", message=msg) # Use callAfter
        except subprocess.CalledProcessError as e:
            print(f"Paste Error (osascript - Code {e.returncode}):\nStderr: {e.stderr}\nStdout: {e.stdout}")
            error_msg = f"Pasting failed (Code {e.returncode})."
            if "not allowed to send keystrokes" in e.stderr or "access" in e.stderr:
                 error_msg += "\nCheck System Settings > Privacy & Security > Automation."
            else:
                 error_msg += f"\n{e.stderr[:200]}..."
            AppHelper.callAfter(rumps.alert, title="Paste Error", message=error_msg) # Use callAfter
        except Exception as e:
            print(f"Unexpected paste error (osascript): {e}")
            msg = f"Unexpected error during paste: {e}"
            AppHelper.callAfter(rumps.alert, title="Paste Error", message=msg) # Use callAfter
        # --- End of osascript Implementation ---
        
        # --- pynput Controller Implementation (Commented out) ---
        # try:
        #     # 1. Put text onto the clipboard (using subprocess/pbcopy for simplicity)
        #     escaped_text_pbcopy = text_to_paste.replace('\\', '\\\\').replace('"', '\\"')
        #     process_pbcopy = subprocess.run(
        #         f'echo "{escaped_text_pbcopy}" | pbcopy',
        #         shell=True, check=True, capture_output=True, text=True
        #     )
        #     if process_pbcopy.stderr:
        #         print(f"pbcopy stderr: {process_pbcopy.stderr.strip()}")
        #     print("Text copied to clipboard.")
        # 
        #     # 2. Simulate Cmd+V keystroke using pynput
        #     time.sleep(0.1) 
        #     keyboard_controller = KeyboardController()
        #     with keyboard_controller.pressed(keyboard.Key.cmd):
        #         keyboard_controller.press('v')
        #         keyboard_controller.release('v')
        #     print("Paste key simulated (Cmd+V)." )
        # 
        # except FileNotFoundError:
        #     print("Error: 'pbcopy' command not found. Cannot copy to clipboard.")
        #     rumps.alert(title="Paste Error", message="pbcopy command not found.")
        # except subprocess.CalledProcessError as e:
        #     print(f"Error copying to clipboard (pbcopy): {e}")
        #     rumps.alert(title="Paste Error", message=f"Failed to copy text to clipboard: {e}")
        # except Exception as e:
        #     print(f"Unexpected paste error (pynput simulation): {e}")
        #     rumps.alert(title="Paste Error", message=f"Unexpected error during paste simulation: {e}")
        # --- End of pynput Controller implementation ---

    # --- Main Processing Logic ---
    def process_dictation_on_release(self):
        recording_data = self.stop_recording() # This sets self.is_recording = False
        if recording_data is not None and recording_data.size > 0:
            temp_file_path = self.save_audio_to_temp_file(recording_data)
            if temp_file_path:
                # Start transcription in a separate thread
                # The thread will handle restarting the timer in its finally block
                transcribe_thread = threading.Thread(target=self._transcribe_and_paste_thread, args=(temp_file_path,), daemon=True)
                transcribe_thread.start()
                return # Return here, timer restart is handled by the thread
            else: 
                print("Failed to save audio.")
        else: 
            print("Empty recording, skipping transcription.")
            


    def _transcribe_and_paste_thread(self, temp_file_path):
        try:
            print("Starting transcription thread...")
            transcribed_text = self.transcribe_audio(temp_file_path)
            if transcribed_text:
                # Convert to Australian English
                converted_text, conversion_time_ms = self.convert_to_australian_english(transcribed_text)
                print(f"Spelling conversion to Australian English took {conversion_time_ms:.3f} ms.")
                
                # Use callAfter for paste as it might interact with UI/clipboard
                AppHelper.callAfter(self.paste_text, converted_text)
            else:
                print("Transcription thread: No text produced.")
        finally:
            # --- Clean up temp file --- 
            try: 
                os.remove(temp_file_path)
                print(f"Removed temp file: {temp_file_path}")
            except OSError as e: 
                print(f"Error removing temp file {temp_file_path}: {e}")
            
            # --- Restart Scan Timer --- 
            # Use callAfter to ensure timer start happens on the main thread
            # Check the flag before attempting to restart
            if self.timer_paused_by_recording:
                # Schedule the restart logic to run on the main thread
                AppHelper.callAfter(self._restart_scan_timer_if_needed)
            # --------------------------
            print("Transcription thread finished.")

    def _restart_scan_timer_if_needed(self):
        """Helper function to restart timer, intended to be called via AppHelper.callAfter"""
        if self.timer_paused_by_recording:  # Double check flag on main thread
            if self.mic_manager.scan_timer: 
                try:
                    self.mic_manager.scan_timer.start()
                except Exception as e:
                    print(f"Error restarting scan timer: {e}")
            self.timer_paused_by_recording = False  # Reset flag

    # --- Keyboard Listener Callbacks ---
    def on_press(self, key):
        if key == self.recording_hotkey:
            self.start_recording()

    def on_release(self, key):
        if key == self.recording_hotkey:
            if self.is_recording:
                self.process_dictation_on_release()


    def show_troubleshooting(self, sender):
        """Show troubleshooting tips."""
        title = "Troubleshooting Tips"
        message = """1. Check microphone is working in System Settings > Sound.
2. Verify whisper.cpp is compiled correctly.
3. Check config.ini paths are correct.
4. Try manually running whisper-cli on a WAV file from the terminal.

AUDIO DEVICE ISSUES (Common after sleep/wake or logout/login):
• If recording fails with "no object with given ID" errors:
  - Use "Refresh Audio Devices" menu option
  - Try "Change Audio Device" to select a different microphone
  - Restart Kataru if problem persists
• Device monitoring now runs automatically every 10 seconds
• The app detects sleep/wake events and auto-refreshes devices

macOS PERMISSIONS: Ensure Kataru has:
   - Microphone Access (System Settings > Privacy & Security > Microphone)
   - Input Monitoring Access (System Settings > Privacy & Security > Input Monitoring) for hotkeys.
   - Accessibility Access (System Settings > Privacy & Security > Accessibility) if text pasting fails.
   The app should request these. If not, or if denied, toggle them.
6. Restart the app after granting permissions."""
        
        rumps.alert(title=title, message=message)
        
    @rumps.clicked("About")
    def about(self, _):
        copyright_notice = "Copyright © 2024 Your Name/Company. All rights reserved."
        repository_url = "https://github.com/your_username/kataru"

        if self.config and self.config.has_section('General'):
            copyright_notice = self.config.get('General', 'copyright_notice', fallback=copyright_notice)
            repository_url = self.config.get('General', 'repository_url', fallback=repository_url)
        elif self.config: # if self.config exists but no General section
             print("Warning: [General] section not found in config for About dialog copyright/repo URL.")


        about_text = f"""Kataru
Version {__version__}

{copyright_notice}

For more information, visit:
{repository_url}

Hotkeys:
- Press and Hold {self.hotkey_str}: Record audio
- Release {self.hotkey_str}: Transcribe audio

Whisper Model: {self.model_path}
Main Executable: {self.main_exec_path}
"""
        rumps.alert(
            title="About Kataru",
            message=about_text,
            ok="OK"
        )

    def on_microphone_changed(self, old_index, new_index, list_changed=False):
        """Handle microphone change events from MicrophoneManager.

        This callback can be triggered for two reasons:
        1. The selected microphone (self.current_mic_index) actually changed.
        2. The list of available microphones changed, even if the selected one didn't.
           In this case, old_index and new_index might be the same.
        """
        old_name = self.mic_manager.get_microphone_name(old_index)
        new_name = self.mic_manager.get_microphone_name(new_index)
        
        # Update app's device_index only if the selected microphone truly changed.
        # The mic_manager.current_mic_index is the source of truth for selection.
        if self.device_index != self.mic_manager.current_mic_index:
            self.device_index = self.mic_manager.current_mic_index
            print(f"App's device_index updated to: {self.device_index} ({new_name})")
            # Persist this change to config only if the selected device changed
            self.update_config_with_new_device()

            # Notify user only if the selected device changed
            message = f"Microphone changed from '{old_name}' to '{new_name}'"
            print(message)
            AppHelper.callAfter(rumps.notification,
                title="Microphone Changed",
                subtitle="",
                message=message
            )
        elif list_changed:
            print(f"Microphone list updated. Current selection remains: {new_name} (Index: {new_index})")

        # Always update the menu to reflect current state (list or selection change)
        AppHelper.callAfter(self.update_microphone_menu)

    def stop(self):
        """Cleanup resources when the app is stopping."""
        print("Stopping application components...")
        
        # Stop device monitoring timer
        if hasattr(self, 'device_monitor_timer') and self.device_monitor_timer is not None:
            if self.device_monitor_timer.is_alive():
                print("Stopping device monitoring timer...")
                self.device_monitor_timer.stop()
            self.device_monitor_timer = None
        
        # Stop microphone scanning timer
        if hasattr(self, 'mic_scan_timer') and self.mic_scan_timer is not None:
            if self.mic_scan_timer.is_alive():
                print("Stopping microphone scan timer...")
                self.mic_scan_timer.stop()
            self.mic_scan_timer = None

        # Stop the microphone manager
        if hasattr(self, 'mic_manager') and self.mic_manager is not None:
            print("Calling MicrophoneManager.stop_monitoring()...")
            self.mic_manager.stop_monitoring()

        # Stop hotkey listener
        if hasattr(self, 'hotkey_listener') and self.hotkey_listener is not None:
            if self.hotkey_listener.is_alive():
                print("Stopping hotkey listener...")
                self.hotkey_listener.stop()
            self.hotkey_listener = None
        
        # Close any active audio stream
        self._close_stream_safely()

        print("Kataru application cleanup finished.")

    @rumps.clicked("Refresh Audio Devices")
    def manual_refresh_devices(self, sender):
        """Manually refresh the list of audio devices."""
        print("Refreshing audio devices...")
        self.mic_manager.scan_devices()
        
        # Force sync if they're out of sync
        if self.device_index != self.mic_manager.current_mic_index:
            if self.mic_manager.current_mic_index is not None and self.mic_manager.current_mic_index != -1:
                self.device_index = self.mic_manager.current_mic_index
                self.update_config_with_new_device()
                print(f"Synced device selection to: {self.mic_manager.get_microphone_name(self.device_index)}")
        
        AppHelper.callAfter(self.update_microphone_menu)
        print("Audio devices refreshed.")

    def setup_system_event_notifications(self):
        """Set up system event notifications for sleep/wake events."""
        try:
            # Get the shared workspace instance
            workspace = NSWorkspace.sharedWorkspace()
            notification_center = workspace.notificationCenter()
            
            # Register for sleep notification
            notification_center.addObserver_selector_name_object_(
                self, 
                objc.selector(self.system_will_sleep, signature=b'v@:@'),
                NSWorkspace.willSleepNotification, 
                None
            )
            
            # Register for wake notification  
            notification_center.addObserver_selector_name_object_(
                self,
                objc.selector(self.system_did_wake, signature=b'v@:@'), 
                NSWorkspace.didWakeNotification,
                None
            )
            
            print("Registered for system sleep/wake notifications")
        except Exception as e:
            print(f"Failed to register for system notifications: {e}")

    def system_will_sleep(self, notification):
        """Called when system is about to sleep."""
        print("System going to sleep - pausing device monitoring")
        if hasattr(self, 'device_monitor_timer') and self.device_monitor_timer is not None:
            if self.device_monitor_timer.is_alive():
                self.device_monitor_timer.stop()

    def system_did_wake(self, notification):
        """Called when system wakes up from sleep."""
        print("System woke up - refreshing devices and resuming monitoring")
        # Force immediate device scan when system wakes up
        self.mic_manager.scan_devices()
        AppHelper.callAfter(self.update_microphone_menu)
        
        # Restart device monitoring timer
        if hasattr(self, 'device_monitor_timer') and self.device_monitor_timer is not None:
            if not self.device_monitor_timer.is_alive():
                self.device_monitor_timer = rumps.Timer(self.mic_manager.scan_devices, self.device_scan_interval)
                self.device_monitor_timer.start()
                print("Restarted device monitoring timer after wake")




# --- Main Execution ---
if __name__ == "__main__":
    print("Starting DictationApp...")
    try:
        app = DictationApp()
        app.run()
    except Exception as e:
        # Catch potential errors during DictationApp.__init__ if rumps isn't running yet
        print(f"Critical error initializing DictationApp: {e}")
        # Attempt to show an alert if rumps was partially loaded
        try: rumps.alert(title="Initialization Error", message=f"Critical error: {e}")
        except: pass
    finally:
        print("DictationApp finished.") 