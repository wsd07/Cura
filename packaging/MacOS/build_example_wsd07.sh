#!/bin/bash

# Example script for building Cura package using wsd07's custom build script
# This script demonstrates how to use the build_macos_package_wsd07.py script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURA_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
URANIUM_ROOT="$(cd "$CURA_ROOT/../Uranium" && pwd)"
DIST_DIR="$CURA_ROOT/dist"

# Get Cura version
get_cura_version() {
    if [ -f "$CURA_ROOT/cura/CuraVersion.py" ]; then
        # Extract version from CuraVersion.py
        VERSION=$(python3 -c "
import sys
sys.path.insert(0, '$CURA_ROOT')
from cura.CuraVersion import CuraVersion
print(CuraVersion)
" 2>/dev/null || echo "5.8.0")
    else
        VERSION="5.8.0"
    fi
    echo "$VERSION"
}

# Print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    log_success "Python 3 found: $(python3 --version)"
    
    # Check if we're in a virtual environment
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        log_success "Virtual environment active: $VIRTUAL_ENV"
    else
        log_warning "No virtual environment detected"
        log_info "It's recommended to use a virtual environment"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
    
    # Check paths
    if [ ! -d "$CURA_ROOT" ]; then
        log_error "Cura root directory not found: $CURA_ROOT"
        exit 1
    fi
    log_success "Cura root found: $CURA_ROOT"
    
    if [ ! -d "$URANIUM_ROOT" ]; then
        log_error "Uranium root directory not found: $URANIUM_ROOT"
        log_info "Expected location: $URANIUM_ROOT"
        exit 1
    fi
    log_success "Uranium root found: $URANIUM_ROOT"
    
    # Check CuraEngine
    if [ ! -f "$CURA_ROOT/CuraEngine.exe" ] && [ ! -f "$CURA_ROOT/CuraEngine" ]; then
        log_error "CuraEngine executable not found in Cura root"
        log_info "Expected: $CURA_ROOT/CuraEngine.exe or $CURA_ROOT/CuraEngine"
        exit 1
    fi
    log_success "CuraEngine executable found"
    
    # Check for create-dmg (optional)
    if command -v create-dmg &> /dev/null; then
        log_success "create-dmg found: $(which create-dmg)"
    else
        log_warning "create-dmg not found. Install with: brew install create-dmg"
        log_info "DMG creation will use fallback method"
    fi
}

# Main build function
build_cura() {
    log_info "Starting Cura build process..."
    
    # Get version
    CURA_VERSION=$(get_cura_version)
    log_info "Cura version: $CURA_VERSION"
    
    # Generate filename
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        ARCH="X64"
    elif [ "$ARCH" = "arm64" ]; then
        ARCH="ARM64"
    fi
    
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    FILENAME="UltiMaker-Cura-${CURA_VERSION}-macOS-${ARCH}-wsd07-${TIMESTAMP}"
    
    log_info "Output filename: $FILENAME"
    
    # Create dist directory
    mkdir -p "$DIST_DIR"
    
    # Run the custom build script
    log_info "Running custom build script..."
    
    python3 "$SCRIPT_DIR/build_macos_package_wsd07.py" \
        --cura-path "$CURA_ROOT" \
        --uranium-path "$URANIUM_ROOT" \
        --dist-path "$DIST_DIR" \
        --app-name "UltiMaker-Cura" \
        --cura-version "$CURA_VERSION" \
        --filename "$FILENAME" \
        --build-dmg \
        "$@"  # Pass any additional arguments
    
    log_success "Build completed!"
    log_info "Output directory: $DIST_DIR"
    
    # List output files
    if [ -d "$DIST_DIR" ]; then
        log_info "Generated files:"
        ls -la "$DIST_DIR" | grep -E "\.(app|dmg|pkg)$" || log_warning "No output files found"
    fi
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Build Cura macOS package using local source code and pre-compiled CuraEngine"
    echo ""
    echo "Options:"
    echo "  --help              Show this help message"
    echo "  --check-only        Only check prerequisites, don't build"
    echo "  --build-pkg         Also build PKG installer (in addition to DMG)"
    echo "  --no-dmg            Don't build DMG installer"
    echo ""
    echo "Environment:"
    echo "  CURA_ROOT:    $CURA_ROOT"
    echo "  URANIUM_ROOT: $URANIUM_ROOT"
    echo "  DIST_DIR:     $DIST_DIR"
    echo ""
    echo "Prerequisites:"
    echo "  - Python 3.8+"
    echo "  - Virtual environment (recommended)"
    echo "  - Cura source code in parallel development mode"
    echo "  - Uranium source code in parallel development mode"
    echo "  - Pre-compiled CuraEngine.exe in Cura root directory"
    echo "  - create-dmg (optional, install with: brew install create-dmg)"
    echo ""
    echo "Example:"
    echo "  $0                    # Build with default settings"
    echo "  $0 --build-pkg        # Build both DMG and PKG"
    echo "  $0 --check-only       # Only check prerequisites"
}

# Parse command line arguments
BUILD_PKG=false
CHECK_ONLY=false
BUILD_DMG=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --help)
            show_usage
            exit 0
            ;;
        --check-only)
            CHECK_ONLY=true
            shift
            ;;
        --build-pkg)
            BUILD_PKG=true
            shift
            ;;
        --no-dmg)
            BUILD_DMG=false
            shift
            ;;
        *)
            # Pass unknown arguments to the Python script
            break
            ;;
    esac
done

# Main execution
main() {
    echo "🚀 Cura macOS Package Builder (wsd07 Custom Version)"
    echo "=================================================="
    
    check_prerequisites
    
    if [ "$CHECK_ONLY" = true ]; then
        log_success "Prerequisites check completed successfully!"
        exit 0
    fi
    
    # Prepare additional arguments
    EXTRA_ARGS=()
    if [ "$BUILD_PKG" = true ]; then
        EXTRA_ARGS+=(--build-pkg)
    fi
    if [ "$BUILD_DMG" = false ]; then
        EXTRA_ARGS+=(--no-dmg)
    fi
    
    # Add remaining command line arguments
    EXTRA_ARGS+=("$@")
    
    build_cura "${EXTRA_ARGS[@]}"
    
    echo ""
    log_success "🎉 All done! Your Cura package is ready."
}

# Run main function
main "$@"
