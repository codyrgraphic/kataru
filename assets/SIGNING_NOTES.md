# Code Signing Notes for Kataru

## Current Status
- App signed with Developer ID Application certificate (production ready)
- Entitlements properly configured in Kataru.entitlements
- Hardened runtime enabled for future notarization
- Privacy permissions embedded and functional

## Signing Details
- **Certificate**: Developer ID Application: Cody Roberts (6L458UBN7J)
- **Entitlements File**: Kataru.entitlements
- **Runtime Options**: Hardened runtime enabled
- **Team ID**: 6L458UBN7J

## For Production Distribution
1. ✅ Developer ID Application certificate configured
2. ✅ Entitlements properly applied
3. ✅ Hardened runtime enabled
4. 🔄 Optional: Notarize for enhanced user experience

## Testing Signed App
```bash
# Verify signature
codesign -dv --verbose=4 dist/Kataru.app

# Check entitlements
codesign -d --entitlements :- dist/Kataru.app

# Remove quarantine if needed
xattr -d com.apple.quarantine dist/Kataru.app
```

## Privacy Permissions Included
- Microphone access (com.apple.security.device.audio-input)
- Speech recognition (com.apple.security.speech-recognition)
- Network client access (com.apple.security.network.client)
- JIT compilation support
- Unsigned executable memory support

## Distribution Ready
The current build is ready for distribution with:
- Professional DMG installer
- Proper code signing
- Privacy permissions
- User documentation included 