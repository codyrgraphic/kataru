#!/usr/bin/env python3

"""Test script to check microphone preferences and selection logic.

This utility helps troubleshoot microphone selection issues by showing:
- Available microphones and their device indices
- Configured preferences from config.ini
- Which microphone would be selected based on preferences
- Current config.ini device_index setting and its validity
"""

import configparser
import sounddevice as sd
import os

def load_microphone_preferences():
    """Load microphone preferences from config.ini."""
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    
    if not os.path.exists(config_path):
        print(f"Error: config.ini not found at {config_path}")
        return {}
    
    config.read(config_path)
    preferences = {}
    
    if config.has_section('microphones'):
        for key, value in config.items('microphones'):
            try:
                name = key.strip('"\\\'')
                priority = int(value)
                preferences[name.lower()] = priority
            except ValueError:
                print(f"Warning: Invalid priority value for microphone {key}: {value}")
    
    return preferences

def get_available_microphones():
    """Get list of available microphones."""
    devices = sd.query_devices()
    microphones = []
    
    for i, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            microphones.append((i, dev['name']))
    
    return microphones

def score_microphones(microphones, preferences):
    """Score microphones based on preferences."""
    scored_mics = []
    
    for idx, name in microphones:
        score = 0
        name_lower = name.lower()
        for pattern, priority in preferences.items():
            if pattern in name_lower:
                score = max(score, priority)
        scored_mics.append((idx, name, score))
    
    scored_mics.sort(key=lambda x: x[2], reverse=True)
    return scored_mics

def main():
    print("=== Microphone Test Script ===\n")
    
    # Load preferences
    preferences = load_microphone_preferences()
    print(f"Loaded preferences from config.ini:")
    for pattern, priority in preferences.items():
        print(f"  '{pattern}' -> priority {priority}")
    print()
    
    # Get available microphones
    microphones = get_available_microphones()
    print(f"Available microphones ({len(microphones)} found):")
    for idx, name in microphones:
        print(f"  {idx}: {name}")
    print()
    
    # Score microphones
    scored_mics = score_microphones(microphones, preferences)
    print("Microphones ranked by preference:")
    for idx, name, score in scored_mics:
        marker = " ← BEST CHOICE" if idx == scored_mics[0][0] else ""
        print(f"  {idx}: {name} (score: {score}){marker}")
    print()
    
    # Show what would be selected
    if scored_mics:
        best_idx, best_name, best_score = scored_mics[0]
        print(f"Based on your preferences, the app would select:")
        print(f"  Device {best_idx}: {best_name} (score: {best_score})")
        
        if best_score == 0:
            print("  Note: No preference match found, using first available device")
    else:
        print("No microphones found!")
    
    # Show current config setting
    config = configparser.ConfigParser()
    config_path = os.path.join(os.path.dirname(__file__), 'config.ini')
    config.read(config_path)
    
    if config.has_section('Audio'):
        current_device = config.get('Audio', 'device_index', fallback='Not set')
        print(f"\nCurrent config.ini device_index: {current_device}")
        
        if current_device.isdigit():
            current_idx = int(current_device)
            current_name = "Unknown"
            for idx, name in microphones:
                if idx == current_idx:
                    current_name = name
                    break
            print(f"  This corresponds to: {current_name}")
            
            # Check if current device is still valid
            valid_indices = [idx for idx, _ in microphones]
            if current_idx not in valid_indices:
                print(f"  WARNING: Device index {current_idx} is no longer available!")

if __name__ == "__main__":
    main() 