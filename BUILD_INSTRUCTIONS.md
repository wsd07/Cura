# Cura Build Instructions

This repository contains custom GitHub Actions workflows for building Cura installers independently from Ultimaker's infrastructure.

## Available Workflows

### 1. Build Installers (`build-installers.yml`)
Main workflow for building production-ready installers for Windows, macOS, and Linux.

**How to use:**
1. Go to the Actions tab in your GitHub repository
2. Select "Build Installers" workflow
3. Click "Run workflow"
4. Configure parameters:
   - **platforms**: Choose which platforms to build (windows,macos,linux)
   - **enterprise**: Build enterprise edition (true/false)
   - **staging**: Use staging API (true/false)

**Outputs:** Installer files for selected platforms

### 2. Build Test (`build-test.yml`)
Quick test build for development and CI.

**Triggers:**
- Automatically on push to main branch
- Automatically on pull requests
- Manually via workflow dispatch

**Purpose:** Fast feedback for code changes

### 3. Release Build (`release.yml`)
Complete release workflow that builds all platforms and creates a GitHub release.

**How to use:**
1. Go to Actions tab
2. Select "Release Build" workflow
3. Click "Run workflow"
4. Enter version number (e.g., 5.8.0)
5. Choose release options (draft/prerelease)

**Outputs:** GitHub release with all platform installers

## Dependencies

All workflows are self-contained and use:
- **Python 3.11**
- **Conan 2.7.0**
- **Custom conan-config** from `wsd07/conan-config`
- Required Python packages: GitPython, requests, pyyaml, jinja2

## Build Times

- **First build**: 1-2 hours (downloads and compiles all dependencies)
- **Subsequent builds**: 30-60 minutes (uses cached dependencies)

## Supported Platforms

- **Windows**: Generates .exe and .msi installers
- **macOS**: Generates .dmg and .pkg installers  
- **Linux**: Generates .AppImage, .deb, and .rpm packages

## Local Development

For local development on macOS:

```bash
# Install dependencies
pip install conan==2.7.0 GitPython requests pyyaml jinja2

# Setup Conan
conan profile detect --force
conan config install https://github.com/wsd07/conan-config.git

# Build Cura
conan install . --build=missing --update
conan build .
```

## Troubleshooting

### Common Issues

1. **"No module named 'git'" error**: Fixed by installing GitPython
2. **Conan config errors**: Using custom conan-config repository
3. **Long build times**: Normal for first build, subsequent builds are faster

### Getting Help

- Check the Actions logs for detailed error messages
- Ensure all required Python packages are installed
- Verify conan-config is accessible

## Repository Structure

- `/.github/workflows/build-installers.yml` - Main installer build workflow
- `/.github/workflows/build-test.yml` - Quick test build workflow
- `/.github/workflows/release.yml` - Release workflow with GitHub releases
- `/conanfile.py` - Conan build configuration
- `/conandata.yml` - Conan package data

## Notes

- All workflows are independent of Ultimaker's infrastructure
- Uses custom conan-config to avoid external dependencies
- Builds are cached for faster subsequent runs
- Supports both community and enterprise builds
