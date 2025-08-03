#!/bin/bash

# Final Cura macOS Package Builder
# ===============================

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🚀 Final Cura macOS Package Builder"
echo "==================================="

# Check if pyinstaller is available
if ! command -v pyinstaller &> /dev/null; then
    log_error "PyInstaller not found. Please install it first."
    exit 1
fi

# Get version
VERSION=$(python3 -c "import sys; sys.path.append('.'); from cura.CuraVersion import CuraVersion; print(CuraVersion)")
ARCH=$(uname -m)
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="UltiMaker-Cura-${VERSION}-macOS-${ARCH}-wsd07-${TIMESTAMP}"

log_info "Version: $VERSION"
log_info "Architecture: $ARCH"
log_info "Filename: $FILENAME"
log_info "PyInstaller: $(pyinstaller --version)"

# Set environment variables
export PYTHONPATH="$(pwd):$(dirname $(pwd))/Uranium:$PYTHONPATH"

# Clean previous builds
rm -rf dist build

# Create simple PyInstaller command
log_info "Starting PyInstaller build..."

pyinstaller \
    --name "UltiMaker-Cura" \
    --windowed \
    --onedir \
    --clean \
    --noconfirm \
    --add-data "cura:cura" \
    --add-data "plugins:plugins" \
    --add-data "resources:resources" \
    --add-data "CuraEngine:." \
    --hidden-import "cura" \
    --hidden-import "UM" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtGui" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtQml" \
    --hidden-import "PyQt6.QtQuick" \
    --hidden-import "sip" \
    --hidden-import "numpy" \
    --hidden-import "scipy" \
    --hidden-import "trimesh" \
    --hidden-import "shapely" \
    --hidden-import "serial" \
    --hidden-import "Arcus" \
    --hidden-import "pynest2d" \
    --hidden-import "Savitar" \
    cura_app.py

# Check if build was successful
if [ -d "dist/UltiMaker-Cura" ]; then
    log_success "✅ Build completed successfully!"
    
    # Create app bundle structure
    log_info "Creating macOS app bundle..."
    cd dist
    mkdir -p "$FILENAME.app/Contents/MacOS"
    mkdir -p "$FILENAME.app/Contents/Resources"
    
    # Move the executable
    mv UltiMaker-Cura/* "$FILENAME.app/Contents/MacOS/"
    
    # Create Info.plist
    cat > "$FILENAME.app/Contents/Info.plist" << 'PLIST_EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>UltiMaker-Cura</string>
    <key>CFBundleIdentifier</key>
    <string>com.ultimaker.cura</string>
    <key>CFBundleName</key>
    <string>UltiMaker-Cura</string>
    <key>CFBundleDisplayName</key>
    <string>UltiMaker Cura</string>
    <key>CFBundleVersion</key>
    <string>5.11.0</string>
    <key>CFBundleShortVersionString</key>
    <string>5.11.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>
PLIST_EOF
    
    # Make executable
    chmod +x "$FILENAME.app/Contents/MacOS/UltiMaker-Cura"
    
    # Create DMG
    log_info "Creating DMG..."
    hdiutil create -volname "$FILENAME" -srcfolder "$FILENAME.app" -ov -format UDZO "$FILENAME.dmg"
    
    # Get file sizes
    APP_SIZE=$(du -sh "$FILENAME.app" | cut -f1)
    DMG_SIZE=$(du -sh "$FILENAME.dmg" | cut -f1)
    
    log_success "📦 Package created successfully!"
    echo "  App size: $APP_SIZE"
    echo "  DMG size: $DMG_SIZE"
    echo "  Location: $(pwd)/$FILENAME.dmg"
    
    log_info "🎉 Build completed at: $(date)"
else
    log_error "❌ Build failed - UltiMaker-Cura directory not found"
    exit 1
fi
