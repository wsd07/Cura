#!/usr/bin/env python3
# Copyright (c) 2023 UltiMaker
# Cura is released under the terms of the LGPLv3 or higher.
# 
# Custom Windows build script for wsd07's development environment
# Features:
# 1. Uses local Cura and Uranium source code
# 2. Uses pre-compiled CuraEngine executable from Cura root directory
# 3. Bypasses conan dependency management for local development

import os
import sys
import argparse
import subprocess
import shutil
import json
import semver
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
from jinja2 import Template

# Configuration
ULTIMAKER_CURA_DOMAIN = os.environ.get("ULTIMAKER_CURA_DOMAIN", "nl.ultimaker.cura")
SCRIPT_DIR = Path(__file__).parent.absolute()
CURA_ROOT = SCRIPT_DIR.parent.parent
URANIUM_ROOT = CURA_ROOT.parent / "Uranium"

class LocalWindowsPackageBuilder:
    """Custom Windows package builder for local development environment"""
    
    def __init__(self, args):
        self.args = args
        self.cura_root = Path(args.cura_path) if args.cura_path else CURA_ROOT
        self.uranium_root = Path(args.uranium_path) if args.uranium_path else URANIUM_ROOT
        self.dist_path = Path(args.dist_path)
        self.app_name = args.app_name
        self.cura_version = args.cura_version
        
        # Validate paths
        self._validate_paths()
        
    def _validate_paths(self):
        """Validate that all required paths exist"""
        if not self.cura_root.exists():
            raise FileNotFoundError(f"Cura root directory not found: {self.cura_root}")
        if not self.uranium_root.exists():
            raise FileNotFoundError(f"Uranium root directory not found: {self.uranium_root}")
        
        # Check CuraEngine (prefer Windows version)
        curaengine_found = False
        curaengine_type = ""
        if (self.cura_root / "CuraEngine.exe").exists():
            curaengine_found = True
            curaengine_type = "CuraEngine.exe (Windows)"
        elif (self.cura_root / "CuraEngine").exists():
            curaengine_found = True
            curaengine_type = "CuraEngine"
        
        if not curaengine_found:
            raise FileNotFoundError(f"CuraEngine not found in Cura root: {self.cura_root}")
        
        print(f"✓ Cura root: {self.cura_root}")
        print(f"✓ Uranium root: {self.uranium_root}")
        print(f"✓ {curaengine_type} found")
        
    def _get_python_site_packages(self) -> Path:
        """Get the site-packages directory of current Python environment"""
        import site
        return Path(site.getsitepackages()[0])
        
    def _prepare_local_environment(self):
        """Prepare local development environment"""
        print("Preparing local development environment...")
        
        # Check if we're using conan environment (preferred for this setup)
        pythonpath = os.environ.get('PYTHONPATH', '')
        if 'Uranium' in pythonpath and 'conan' in pythonpath:
            print("✓ Detected conan environment with Uranium in PYTHONPATH")
            print("✓ Using existing conan-managed dependencies")
        else:
            print("⚠️  Warning: Not using conan environment")
            print("⚠️  This script is designed to work with conan environment")
            print("⚠️  Please run: .\\build\\generators\\conanrun.bat")
        
        # Install PyInstaller if not available
        print("Checking PyInstaller...")
        try:
            import PyInstaller
            print("✓ PyInstaller already available")
        except ImportError:
            print("Installing PyInstaller...")
            try:
                subprocess.run([
                    sys.executable, "-m", "pip", "install", "PyInstaller>=5.0"
                ], check=True, capture_output=True)
                print("✓ Installed PyInstaller")
            except subprocess.CalledProcessError as e:
                print(f"❌ Failed to install PyInstaller: {e}")
                raise
        
        # Test imports to verify environment
        print("Testing imports...")
        try:
            # Test Uranium import
            sys.path.insert(0, str(self.uranium_root))
            import UM
            print("✓ Uranium import successful")
        except ImportError as e:
            print(f"❌ Failed to import Uranium: {e}")
            print("Make sure Uranium is in PYTHONPATH or run with conan environment")
            raise
            
        try:
            # Test Cura import
            sys.path.insert(0, str(self.cura_root))
            import cura
            print("✓ Cura import successful")
        except ImportError as e:
            print(f"❌ Failed to import Cura: {e}")
            print("Make sure Cura is in PYTHONPATH or run with conan environment")
            raise
            
        # Test other required imports
        required_modules = ['PyQt6', 'numpy', 'trimesh']
        for module in required_modules:
            try:
                __import__(module)
                print(f"✓ {module} available")
            except ImportError:
                print(f"⚠️  {module} not available - may cause issues")
                
        print("✓ Environment preparation completed")
        
    def _generate_pyinstaller_spec(self) -> Path:
        """Generate PyInstaller spec file for local Windows build"""
        spec_path = self.cura_root / "UltiMaker-Cura-Windows-Local.spec"
        
        # Collect data files
        datas = self._collect_data_files()
        
        # Collect binary files
        binaries = self._collect_binary_files()
        
        # Hidden imports (based on official conandata.yml)
        hiddenimports = [
            'pySavitar',
            'pyArcus', 
            'pyDulcificum',
            'pynest2d',
            'cura',
            'UM',
            'PyQt6',
            'PyQt6.QtCore',
            'PyQt6.QtGui',
            'PyQt6.QtWidgets',
            'PyQt6.QtQml',
            'PyQt6.QtQuick',
            'PyQt6.QtOpenGL',
            'PyQt6.QtNetwork',
            'PyQt6.sip',
            'logging.handlers',
            'zeroconf',
            'stl',
            'serial',
            'pkgutil',
            'numpy',
            'scipy',
            'trimesh',
            'shapely',
            'sqlite3',
            'Charon',
            'win32ctypes',
            'keyrings.alt',
        ]
        
        # Collect all modules (like official conan build)
        collect_all_modules = [
            'cura',
            'UM', 
            'serial',
            'Charon',
            'sqlite3',
            'trimesh',
            'win32ctypes',
            'PyQt6.QtNetwork',
            'PyQt6.sip',
            'stl',
            'keyrings.alt',
        ]
        
        # Generate spec content
        spec_content = self._generate_spec_content(datas, binaries, hiddenimports, collect_all_modules)
        
        # Write spec file
        with open(spec_path, 'w') as f:
            f.write(spec_content)
            
        print(f"Generated PyInstaller spec: {spec_path}")
        return spec_path
        
    def _collect_data_files(self) -> List[tuple]:
        """Collect data files for PyInstaller"""
        datas = []
        
        print("Collecting data files...")
        
        # Cura resources
        cura_resources = self.cura_root / "resources"
        if cura_resources.exists():
            datas.append((str(cura_resources), "share/cura/resources"))
            print(f"✓ Added Cura resources: {cura_resources}")
        else:
            print(f"⚠️  Cura resources not found: {cura_resources}")
            
        # Cura plugins
        cura_plugins = self.cura_root / "plugins"
        if cura_plugins.exists():
            datas.append((str(cura_plugins), "share/cura/plugins"))
            print(f"✓ Added Cura plugins: {cura_plugins}")
        else:
            print(f"⚠️  Cura plugins not found: {cura_plugins}")
            
        # Uranium resources
        uranium_resources = self.uranium_root / "resources"
        if uranium_resources.exists():
            datas.append((str(uranium_resources), "share/uranium/resources"))
            print(f"✓ Added Uranium resources: {uranium_resources}")
        else:
            print(f"⚠️  Uranium resources not found: {uranium_resources}")
            
        # Uranium plugins
        uranium_plugins = self.uranium_root / "plugins"
        if uranium_plugins.exists():
            datas.append((str(uranium_plugins), "share/uranium/plugins"))
            print(f"✓ Added Uranium plugins: {uranium_plugins}")
        else:
            print(f"⚠️  Uranium plugins not found: {uranium_plugins}")
            
        # Try to find Uranium QML files in different locations
        uranium_qml_locations = [
            self._get_python_site_packages() / "UM" / "Qt" / "qml" / "UM",
            self.uranium_root / "UM" / "Qt" / "qml" / "UM",
            Path(sys.prefix) / "lib" / "site-packages" / "UM" / "Qt" / "qml" / "UM"
        ]
        
        uranium_qml_found = False
        for qml_path in uranium_qml_locations:
            if qml_path.exists():
                datas.append((str(qml_path), "PyQt6/Qt6/qml/UM"))
                print(f"✓ Added Uranium QML files: {qml_path}")
                uranium_qml_found = True
                break
                
        if not uranium_qml_found:
            print("⚠️  Uranium QML files not found in any expected location")
            
        # Add license files
        license_files = [
            self.cura_root / "LICENSE",
            self.cura_root / "packaging" / "cura_license.txt",
            self.uranium_root / "LICENSE"
        ]
        
        for license_file in license_files:
            if license_file.exists():
                datas.append((str(license_file), "share/licenses"))
                print(f"✓ Added license: {license_file}")
                
        # Add version info
        version_files = [
            self.cura_root / "cura" / "CuraVersion.py",
            self.uranium_root / "UM" / "Version.py"
        ]
        
        for version_file in version_files:
            if version_file.exists():
                datas.append((str(version_file), "share/version"))
                print(f"✓ Added version file: {version_file}")
        
        print(f"Total data files collected: {len(datas)}")
        return datas
