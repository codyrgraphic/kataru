#!/bin/bash

# TARGETED Kataru Permission Reset Script
# This script only affects com.codyroberts.kataru and related files

echo "🎯 TARGETED Kataru Permission Reset"
echo "This script only affects Kataru-specific permissions and data"
echo "=========================================="

# Kataru bundle identifier
BUNDLE_ID="com.codyroberts.kataru"

echo "1. Resetting Kataru-specific privacy permissions..."
# Only reset permissions for Kataru specifically
tccutil reset Microphone $BUNDLE_ID 2>/dev/null || echo "   - Microphone: not set"
tccutil reset SpeechRecognition $BUNDLE_ID 2>/dev/null || echo "   - Speech Recognition: not set"  
tccutil reset Accessibility $BUNDLE_ID 2>/dev/null || echo "   - Accessibility: not set"
tccutil reset SystemPolicyAllFiles $BUNDLE_ID 2>/dev/null || echo "   - Full Disk Access: not set"
tccutil reset AppleEvents $BUNDLE_ID 2>/dev/null || echo "   - Apple Events: not set"
tccutil reset ListenEvent $BUNDLE_ID 2>/dev/null || echo "   - Input Monitoring: not set"

echo "2. Removing Kataru application data..."
# Remove Kataru-specific preference files
rm -f ~/Library/Preferences/$BUNDLE_ID.plist 2>/dev/null || echo "   - No preferences found"
rm -rf ~/Library/Application\ Support/Kataru 2>/dev/null || echo "   - No app support data found"
rm -rf ~/Library/Caches/$BUNDLE_ID 2>/dev/null || echo "   - No cache data found"

echo "3. Stopping any running Kataru processes..."
# Only kill Kataru processes, not system daemons
pkill -f "Kataru" 2>/dev/null || echo "   - No Kataru processes running"

echo "4. Clearing Kataru from Launch Services..."
# More targeted launch services reset
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -u ~/Applications/Kataru.app 2>/dev/null || echo "   - App not in ~/Applications"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -u /Applications/Kataru.app 2>/dev/null || echo "   - App not in /Applications"

echo ""
echo "✅ Targeted reset complete!"
echo ""
echo "WHAT WAS RESET:"
echo "• Only Kataru's privacy permissions (not other apps)"
echo "• Kataru preference files and cache data"
echo "• Kataru launch services registration"
echo ""
echo "WHAT WAS NOT AFFECTED:"
echo "• Other apps' privacy permissions"
echo "• System settings and preferences"
echo "• Other applications' data"
echo ""
echo "NEXT STEPS:"
echo "1. Install fresh Kataru from DMG"
echo "2. Launch and test privacy permission flow"
echo "3. All other apps should retain their permissions"
echo ""
echo "Note: This targeted approach should not affect System Settings." 