#!/bin/bash
#
# Cura Translation Compiler Script
# =================================
#
# This script compiles .po translation files to .mo binary files for Cura internationalization.
# It processes both Cura and Uranium translation files.
#
# Usage:
#   ./compile_translations.sh
#
# Requirements:
#   - msgfmt tool (from gettext package)
#   - bash shell
#

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
COMPILED_COUNT=0
FAILED_COUNT=0

# Function to print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# Function to check if msgfmt is available
check_msgfmt() {
    if ! command -v msgfmt &> /dev/null; then
        print_status $RED "ERROR: msgfmt not found. Please install gettext tools."
        echo "On macOS: brew install gettext"
        echo "On Ubuntu/Debian: sudo apt-get install gettext"
        echo "On Windows: Install gettext from https://mlocati.github.io/articles/gettext-iconv-windows.html"
        exit 1
    fi
    
    local version=$(msgfmt --version | head -n1)
    print_status $GREEN "Found msgfmt: $version"
}

# Function to compile a single .po file
compile_po_file() {
    local po_file=$1
    local po_dir=$(dirname "$po_file")
    local po_basename=$(basename "$po_file" .po)
    local locale=$(basename "$po_dir")
    
    # Create LC_MESSAGES directory
    local lc_messages_dir="$po_dir/LC_MESSAGES"
    mkdir -p "$lc_messages_dir"
    
    # Output .mo file path
    local mo_file="$lc_messages_dir/$po_basename.mo"
    
    # Compile .po to .mo
    if msgfmt "$po_file" -o "$mo_file" -f 2>/dev/null; then
        print_status $GREEN "✓ Compiled: $po_file -> $mo_file"
        ((COMPILED_COUNT++))
        return 0
    else
        print_status $RED "✗ Failed to compile: $po_file"
        ((FAILED_COUNT++))
        return 1
    fi
}

# Function to clean existing .mo files and LC_MESSAGES directories
clean_mo_files() {
    local i18n_dir=$1
    
    if [ ! -d "$i18n_dir" ]; then
        return
    fi
    
    print_status $YELLOW "Cleaning existing .mo files in $i18n_dir..."
    
    # Remove .mo files
    find "$i18n_dir" -name "*.mo" -type f -delete 2>/dev/null || true
    
    # Remove empty LC_MESSAGES directories
    find "$i18n_dir" -name "LC_MESSAGES" -type d -empty -delete 2>/dev/null || true
}

# Function to compile translations in a directory
compile_translations_in_directory() {
    local i18n_dir=$1
    local dir_name=$2
    
    if [ ! -d "$i18n_dir" ]; then
        print_status $YELLOW "Warning: Directory $i18n_dir does not exist, skipping..."
        return
    fi
    
    print_status $BLUE "\nProcessing $dir_name translations in: $i18n_dir"
    
    # Find and compile all .po files
    local po_files_found=0
    while IFS= read -r -d '' po_file; do
        po_files_found=1
        compile_po_file "$po_file"
    done < <(find "$i18n_dir" -name "*.po" -type f -print0 2>/dev/null)
    
    if [ $po_files_found -eq 0 ]; then
        print_status $YELLOW "No .po files found in $i18n_dir"
    fi
}

# Main function
main() {
    print_status $BLUE "Cura Translation Compiler"
    print_status $BLUE "========================="
    
    # Check if msgfmt is available
    check_msgfmt
    
    # Get script directory
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Define translation directories
    CURA_I18N="$SCRIPT_DIR/resources/i18n"
    URANIUM_I18N="$SCRIPT_DIR/../Uranium/resources/i18n"
    
    # Clean existing .mo files first
    print_status $YELLOW "\nCleaning existing .mo files..."
    clean_mo_files "$CURA_I18N"
    clean_mo_files "$URANIUM_I18N"
    
    # Compile Cura translations
    print_status $BLUE "\n=================================================="
    print_status $BLUE "COMPILING CURA TRANSLATIONS"
    print_status $BLUE "=================================================="
    compile_translations_in_directory "$CURA_I18N" "Cura"
    
    # Compile Uranium translations
    print_status $BLUE "\n=================================================="
    print_status $BLUE "COMPILING URANIUM TRANSLATIONS"
    print_status $BLUE "=================================================="
    compile_translations_in_directory "$URANIUM_I18N" "Uranium"
    
    # Summary
    print_status $BLUE "\n=================================================="
    print_status $BLUE "COMPILATION SUMMARY"
    print_status $BLUE "=================================================="
    print_status $GREEN "Successfully compiled: $COMPILED_COUNT files"
    
    if [ $FAILED_COUNT -gt 0 ]; then
        print_status $RED "Failed to compile: $FAILED_COUNT files"
        print_status $YELLOW "\nWarning: $FAILED_COUNT files failed to compile."
        print_status $YELLOW "Check the error messages above for details."
        exit 1
    elif [ $COMPILED_COUNT -eq 0 ]; then
        print_status $YELLOW "\nNo translation files found to compile."
        exit 1
    else
        print_status $GREEN "\n✓ All $COMPILED_COUNT translation files compiled successfully!"
        print_status $GREEN "\nYou can now restart Cura and the translations should work."
    fi
}

# Run main function
main "$@"
