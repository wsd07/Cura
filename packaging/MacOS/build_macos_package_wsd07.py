#!/usr/bin/env python3
# Copyright (c) 2023 UltiMaker
# Cura is released under the terms of the LGPLv3 or higher.
# 
# Custom build script for wsd07's development environment
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
from pathlib import Path
from typing import List, Dict, Any

# Configuration
ULTIMAKER_CURA_DOMAIN = os.environ.get("ULTIMAKER_CURA_DOMAIN", "nl.ultimaker.cura")
SCRIPT_DIR = Path(__file__).parent.absolute()
CURA_ROOT = SCRIPT_DIR.parent.parent
URANIUM_ROOT = CURA_ROOT.parent / "Uranium"

class LocalPackageBuilder:
    """Custom package builder for local development environment"""
    
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
        # Check CuraEngine (prefer macOS version)
        curaengine_found = False
        curaengine_type = ""
        if (self.cura_root / "CuraEngine").exists():
            curaengine_found = True
            curaengine_type = "CuraEngine (macOS)"
        elif (self.cura_root / "CuraEngine.exe").exists():
            curaengine_found = True
            curaengine_type = "CuraEngine.exe"

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
            print("⚠️  Please run: source build/generators/conanrun.sh")

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
        """Generate PyInstaller spec file for local build"""
        spec_path = self.cura_root / "UltiMaker-Cura-Local.spec"
        
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
            'fcntl',
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
            Path(sys.prefix) / "lib" / "python3.12" / "site-packages" / "UM" / "Qt" / "qml" / "UM"
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
        
    def _collect_binary_files(self) -> List[tuple]:
        """Collect binary files for PyInstaller"""
        binaries = []

        print("Collecting binary files...")

        # Add CuraEngine executable (prefer macOS version)
        # For macOS app bundles, we need to put CuraEngine in the right location
        curaengine_paths = [
            self.cura_root / "CuraEngine",      # macOS version (preferred)
            self.cura_root / "CuraEngine.exe"   # Windows version (fallback)
        ]

        curaengine_found = False
        for engine_path in curaengine_paths:
            if engine_path.exists():
                # Put CuraEngine in both locations to ensure it's found
                binaries.append((str(engine_path), "."))  # Root of bundle
                binaries.append((str(engine_path), "bin"))  # bin directory
                print(f"✓ Added CuraEngine: {engine_path} (to . and bin)")
                curaengine_found = True
                break

        if not curaengine_found:
            raise FileNotFoundError("CuraEngine executable not found in Cura root directory")

        # Collect dynamic libraries from conan environment
        print("Collecting dynamic libraries from conan environment...")

        # Get conan library paths from environment
        dyld_library_path = os.environ.get('DYLD_LIBRARY_PATH', '')
        ld_library_path = os.environ.get('LD_LIBRARY_PATH', '')

        library_paths = []
        for path_env in [dyld_library_path, ld_library_path]:
            if path_env:
                library_paths.extend(path_env.split(':'))

        # Add common library locations
        library_paths.extend([
            str(self.cura_root / "lib"),
            str(self.cura_root / "venv" / "lib"),
            str(Path(sys.prefix) / "lib"),
        ])

        # Collect .dylib and .so files
        for lib_path in library_paths:
            lib_dir = Path(lib_path)
            if lib_dir.exists():
                for pattern in ["*.dylib", "*.so", "*.so.*"]:
                    for lib_file in lib_dir.glob(pattern):
                        if lib_file.is_file():
                            binaries.append((str(lib_file), "."))
                            print(f"✓ Added library: {lib_file.name}")

        # Collect PyQt6 binaries (critical for GUI)
        site_packages = self._get_python_site_packages()
        pyqt6_path = site_packages / "PyQt6"
        if pyqt6_path.exists():
            print("Collecting PyQt6 binaries...")
            for pattern in ["**/*.dylib", "**/*.so"]:
                for qt_file in pyqt6_path.glob(pattern):
                    if qt_file.is_file():
                        binaries.append((str(qt_file), "."))
                        print(f"✓ Added PyQt6 binary: {qt_file.name}")

        print(f"Total binary files collected: {len(binaries)}")
        return binaries
        
    def _generate_spec_content(self, datas: List[tuple], binaries: List[tuple], hiddenimports: List[str], collect_all_modules: List[str]) -> str:
        """Generate PyInstaller spec file content"""
        
        # Convert lists to string representation
        datas_str = "[\n" + ",\n".join([f"    {repr(data)}" for data in datas]) + "\n]"
        binaries_str = "[\n" + ",\n".join([f"    {repr(binary)}" for binary in binaries]) + "\n]"
        hiddenimports_str = "[\n" + ",\n".join([f"    {repr(imp)}" for imp in hiddenimports]) + "\n]"
        
        icon_path = self.cura_root / "packaging" / "icons" / "Cura.icns"
        entitlements_path = self.cura_root / "packaging" / "MacOS" / "cura.entitlements"
        
        # Convert collect_all modules to string
        collect_all_str = "[\n" + ",\n".join([f"    {repr(module)}" for module in collect_all_modules]) + "\n]"

        spec_content = f'''# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for local Cura build

import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

block_cipher = None

datas = {datas_str}
binaries = {binaries_str}
hiddenimports = {hiddenimports_str}

# Collect all modules (like official conan build)
collect_all_modules = {collect_all_str}
for module in collect_all_modules:
    try:
        tmp_ret = collect_all(module)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
        print(f"✓ Collected all for module: {{module}}")
    except Exception as e:
        print(f"⚠️  Failed to collect all for {{module}}: {{e}}")

a = Analysis(
    ['{self.cura_root / "cura_app.py"}'],
    pathex=['{self.cura_root}', '{self.uranium_root}'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='{self.app_name}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=os.getenv('CODESIGN_IDENTITY', None),
    entitlements_file='{entitlements_path}' if Path('{entitlements_path}').exists() else None,
    icon='{icon_path}' if Path('{icon_path}').exists() else None,
    contents_directory='.'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{self.app_name}'
)

app = BUNDLE(
    coll,
    name='{self.app_name}.app',
    icon='{icon_path}' if Path('{icon_path}').exists() else None,
    bundle_identifier='{ULTIMAKER_CURA_DOMAIN}',
    info_plist={{
        'CFBundleDisplayName': '{self.app_name}',
        'CFBundleVersion': '{self.cura_version}',
        'CFBundleShortVersionString': '{self.cura_version}',
        'NSHighResolutionCapable': True,
        'NSRequiresAquaSystemAppearance': False,
    }}
)
'''
        return spec_content
        
    def build_app(self):
        """Build the macOS application"""
        print("🚀 Building macOS application...")

        # Prepare environment
        self._prepare_local_environment()

        # Generate PyInstaller spec
        spec_path = self._generate_pyinstaller_spec()

        # Create dist directory
        self.dist_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created output directory: {self.dist_path}")

        # Clean previous builds
        app_path = self.dist_path / f"{self.app_name}.app"
        if app_path.exists():
            print(f"Cleaning previous build: {app_path}")
            shutil.rmtree(app_path)

        # Run PyInstaller
        cmd = [
            sys.executable, "-m", "PyInstaller",
            "--clean",
            "--noconfirm",
            "--distpath", str(self.dist_path),
            "--workpath", str(self.dist_path / "build"),
            "--log-level", "INFO",
            str(spec_path)
        ]

        print(f"Running PyInstaller...")
        print(f"Command: {' '.join(cmd)}")

        try:
            result = subprocess.run(cmd, check=True, cwd=self.cura_root,
                                  capture_output=True, text=True)
            print("✓ PyInstaller completed successfully")

            # Print some output for debugging
            if result.stdout:
                print("PyInstaller output (last 10 lines):")
                for line in result.stdout.split('\n')[-10:]:
                    if line.strip():
                        print(f"  {line}")

        except subprocess.CalledProcessError as e:
            print(f"❌ PyInstaller failed with return code {e.returncode}")
            if e.stdout:
                print("STDOUT:")
                print(e.stdout)
            if e.stderr:
                print("STDERR:")
                print(e.stderr)
            raise

        # Verify the app was created
        if not app_path.exists():
            raise FileNotFoundError(f"Application was not created: {app_path}")

        # Fix CuraEngine permissions
        self._fix_curaengine_permissions(app_path)

        # Check app size
        app_size = self._get_directory_size(app_path)
        print(f"✓ Application built successfully: {app_path}")
        print(f"  Application size: {app_size:.1f} MB")

        if app_size < 50:
            print("⚠️  Warning: Application size seems unusually small")
        elif app_size > 2000:
            print("⚠️  Warning: Application size seems unusually large")

    def _fix_curaengine_permissions(self, app_path: Path):
        """Fix CuraEngine executable permissions"""
        print("Fixing CuraEngine permissions...")

        # Find CuraEngine in the app bundle - check all possible locations
        curaengine_paths = [
            app_path / "Contents" / "Resources" / "CuraEngine",      # macOS version (preferred)
            app_path / "Contents" / "Resources" / "CuraEngine.exe",  # Windows version
            app_path / "Contents" / "Resources" / "bin" / "CuraEngine",
            app_path / "Contents" / "Resources" / "bin" / "CuraEngine.exe",
            app_path / "Contents" / "MacOS" / "CuraEngine",
            app_path / "Contents" / "MacOS" / "CuraEngine.exe"
        ]

        curaengine_found = False
        for engine_path in curaengine_paths:
            if engine_path.exists():
                # Make executable
                os.chmod(engine_path, 0o755)
                print(f"✓ Fixed permissions for: {engine_path}")
                curaengine_found = True

        if not curaengine_found:
            print("⚠️  Warning: CuraEngine not found in expected locations")

        # Also check for any other executables that might need permissions
        executable_count = 0
        for root, dirs, files in os.walk(app_path):
            for file in files:
                filepath = Path(root) / file
                if file.endswith(('.exe', '.dylib', '.so')) or 'Engine' in file:
                    try:
                        os.chmod(filepath, 0o755)
                        executable_count += 1
                        if 'Engine' in file:
                            print(f"✓ Fixed permissions for: {filepath}")
                    except OSError:
                        pass  # Ignore permission errors

        print(f"✓ Fixed permissions for {executable_count} executable files")

    def _get_directory_size(self, path: Path) -> float:
        """Get directory size in MB"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size / (1024 * 1024)  # Convert to MB
        
    def create_dmg(self):
        """Create DMG installer"""
        if not self.args.build_dmg:
            return

        print("📦 Creating DMG installer...")

        try:
            # Import the original DMG creation function
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_macos import create_dmg

            filename = f"{self.args.filename}.dmg"
            app_name = f"{self.app_name}.app"

            # Verify app exists before creating DMG
            app_path = self.dist_path / app_name
            if not app_path.exists():
                raise FileNotFoundError(f"Application not found: {app_path}")

            create_dmg(filename, str(self.dist_path), str(self.cura_root), app_name)

            dmg_path = self.dist_path / filename
            if dmg_path.exists():
                dmg_size = dmg_path.stat().st_size / (1024 * 1024)  # MB
                print(f"✓ DMG created: {dmg_path}")
                print(f"  DMG size: {dmg_size:.1f} MB")
            else:
                print("⚠️  DMG creation completed but file not found")

        except ImportError as e:
            print(f"❌ Failed to import DMG creation function: {e}")
            print("Falling back to manual DMG creation...")
            self._create_dmg_manual()
        except Exception as e:
            print(f"❌ DMG creation failed: {e}")
            raise

    def _create_dmg_manual(self):
        """Manual DMG creation as fallback"""
        print("Creating DMG manually...")

        filename = f"{self.args.filename}.dmg"
        app_name = f"{self.app_name}.app"

        # Use create-dmg if available
        try:
            cmd = [
                "create-dmg",
                "--window-pos", "640", "360",
                "--window-size", "690", "503",
                "--app-drop-link", "520", "272",
                "--icon-size", "90",
                "--icon", app_name, "169", "272",
                "--hdiutil-quiet",
                str(self.dist_path / filename),
                str(self.dist_path / app_name)
            ]

            subprocess.run(cmd, check=True)
            print(f"✓ DMG created manually: {self.dist_path / filename}")

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"❌ Manual DMG creation failed: {e}")
            print("Please install create-dmg: brew install create-dmg")

    def create_pkg(self):
        """Create PKG installer"""
        if not self.args.build_pkg:
            return

        print("📦 Creating PKG installer...")

        try:
            # Import the original PKG creation function
            sys.path.insert(0, str(SCRIPT_DIR))
            from build_macos import create_pkg_installer

            filename = f"{self.args.filename}.pkg"
            app_name = f"{self.app_name}.app"

            # Verify app exists before creating PKG
            app_path = self.dist_path / app_name
            if not app_path.exists():
                raise FileNotFoundError(f"Application not found: {app_path}")

            create_pkg_installer(filename, str(self.dist_path), self.cura_version, app_name)

            pkg_path = self.dist_path / filename
            if pkg_path.exists():
                pkg_size = pkg_path.stat().st_size / (1024 * 1024)  # MB
                print(f"✓ PKG created: {pkg_path}")
                print(f"  PKG size: {pkg_size:.1f} MB")
            else:
                print("⚠️  PKG creation completed but file not found")

        except ImportError as e:
            print(f"❌ Failed to import PKG creation function: {e}")
        except Exception as e:
            print(f"❌ PKG creation failed: {e}")
            raise


def main():
    parser = argparse.ArgumentParser(description="Build Cura package using local source code")
    parser.add_argument("--cura-path", type=str, help="Path to Cura source directory")
    parser.add_argument("--uranium-path", type=str, help="Path to Uranium source directory") 
    parser.add_argument("--dist-path", required=True, type=str, help="Output directory for built application")
    parser.add_argument("--app-name", default="UltiMaker-Cura", help="Application name")
    parser.add_argument("--cura-version", required=True, type=str, help="Cura version")
    parser.add_argument("--filename", required=True, type=str, help="Output filename (without extension)")
    parser.add_argument("--build-dmg", action="store_true", default=True, help="Build DMG installer")
    parser.add_argument("--build-pkg", action="store_true", default=False, help="Build PKG installer")
    
    args = parser.parse_args()
    
    try:
        builder = LocalPackageBuilder(args)
        builder.build_app()
        builder.create_dmg()
        builder.create_pkg()
        
        print("\n🎉 Build completed successfully!")
        print(f"Output directory: {args.dist_path}")
        
    except Exception as e:
        print(f"❌ Build failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
