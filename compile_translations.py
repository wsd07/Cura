#!/usr/bin/env python3
"""
Cura Translation Compiler
=========================

This script compiles .po translation files to .mo binary files for Cura internationalization.
It processes both Cura and Uranium translation files.

Usage:
    python compile_translations.py

The script will:
1. Find all .po files in resources/i18n directories
2. Compile them to .mo files using msgfmt
3. Place .mo files in the correct LC_MESSAGES directory structure
4. Handle both Cura and Uranium translations

Requirements:
- msgfmt tool (from gettext package)
- Python 3.6+
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

def find_msgfmt():
    """Find msgfmt executable."""
    try:
        result = subprocess.run(['msgfmt', '--version'], 
                              capture_output=True, text=True, check=True)
        print(f"Found msgfmt: {result.stdout.split()[0]} {result.stdout.split()[2]}")
        return 'msgfmt'
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ERROR: msgfmt not found. Please install gettext tools.")
        print("On macOS: brew install gettext")
        print("On Ubuntu/Debian: sudo apt-get install gettext")
        print("On Windows: Install gettext from https://mlocati.github.io/articles/gettext-iconv-windows.html")
        return None

def compile_po_file(po_file_path, output_dir):
    """Compile a single .po file to .mo file."""
    po_path = Path(po_file_path)
    
    # Create the LC_MESSAGES directory structure
    locale = po_path.parent.name
    mo_dir = Path(output_dir) / locale / "LC_MESSAGES"
    mo_dir.mkdir(parents=True, exist_ok=True)
    
    # Determine the domain name from the .po filename
    domain = po_path.stem
    mo_file = mo_dir / f"{domain}.mo"
    
    try:
        # Compile .po to .mo
        cmd = ['msgfmt', str(po_path), '-o', str(mo_file), '-f']
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)

        # Use absolute paths to avoid relative path issues
        try:
            po_rel = po_path.relative_to(Path.cwd())
            mo_rel = mo_file.relative_to(Path.cwd())
            print(f"✓ Compiled: {po_rel} -> {mo_rel}")
        except ValueError:
            # If relative path fails, use absolute paths
            print(f"✓ Compiled: {po_path} -> {mo_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to compile {po_path}: {e.stderr}")
        return False

def compile_translations_in_directory(i18n_dir, output_dir=None):
    """Compile all .po files in a directory."""
    i18n_path = Path(i18n_dir)
    if not i18n_path.exists():
        print(f"Warning: Directory {i18n_dir} does not exist, skipping...")
        return 0, 0
    
    if output_dir is None:
        output_dir = i18n_path
    
    print(f"\nProcessing translations in: {i18n_path}")
    
    # Find all .po files
    po_files = list(i18n_path.glob("**/*.po"))
    if not po_files:
        print(f"No .po files found in {i18n_path}")
        return 0, 0
    
    compiled_count = 0
    failed_count = 0
    
    for po_file in po_files:
        if compile_po_file(po_file, output_dir):
            compiled_count += 1
        else:
            failed_count += 1
    
    return compiled_count, failed_count

def clean_mo_files(i18n_dir):
    """Remove existing .mo files."""
    i18n_path = Path(i18n_dir)
    if not i18n_path.exists():
        return
    
    mo_files = list(i18n_path.glob("**/*.mo"))
    lc_messages_dirs = list(i18n_path.glob("**/LC_MESSAGES"))
    
    for mo_file in mo_files:
        mo_file.unlink()
        print(f"Removed: {mo_file}")
    
    for lc_dir in lc_messages_dirs:
        if lc_dir.is_dir() and not any(lc_dir.iterdir()):
            lc_dir.rmdir()
            print(f"Removed empty directory: {lc_dir}")

def main():
    """Main function."""
    print("Cura Translation Compiler")
    print("=" * 50)
    
    # Check if msgfmt is available
    msgfmt_cmd = find_msgfmt()
    if not msgfmt_cmd:
        sys.exit(1)
    
    # Get script directory
    script_dir = Path(__file__).parent.absolute()
    
    # Define translation directories
    cura_i18n = script_dir / "resources" / "i18n"
    uranium_i18n = script_dir.parent / "Uranium" / "resources" / "i18n"
    
    total_compiled = 0
    total_failed = 0
    
    # Clean existing .mo files first
    print("\nCleaning existing .mo files...")
    if cura_i18n.exists():
        clean_mo_files(cura_i18n)
    if uranium_i18n.exists():
        clean_mo_files(uranium_i18n)
    
    # Compile Cura translations
    print("\n" + "=" * 50)
    print("COMPILING CURA TRANSLATIONS")
    print("=" * 50)
    compiled, failed = compile_translations_in_directory(cura_i18n)
    total_compiled += compiled
    total_failed += failed
    
    # Compile Uranium translations
    print("\n" + "=" * 50)
    print("COMPILING URANIUM TRANSLATIONS")
    print("=" * 50)
    compiled, failed = compile_translations_in_directory(uranium_i18n)
    total_compiled += compiled
    total_failed += failed
    
    # Summary
    print("\n" + "=" * 50)
    print("COMPILATION SUMMARY")
    print("=" * 50)
    print(f"Successfully compiled: {total_compiled} files")
    print(f"Failed to compile: {total_failed} files")
    
    if total_failed > 0:
        print(f"\nWarning: {total_failed} files failed to compile.")
        print("Check the error messages above for details.")
        sys.exit(1)
    elif total_compiled == 0:
        print("\nNo translation files found to compile.")
        sys.exit(1)
    else:
        print(f"\n✓ All {total_compiled} translation files compiled successfully!")
        print("\nYou can now restart Cura and the translations should work.")

if __name__ == "__main__":
    main()
