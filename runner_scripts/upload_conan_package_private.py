import argparse
import os
import subprocess
import json


def upload_conan_package(args):
    """
    Modified upload script for private development.
    This script lists packages but skips actual upload to avoid authentication issues.
    """
    try:
        packages_json = subprocess.run(["conan", "list", "-c", "-f", "json", args.package], capture_output=True, check=True).stdout
        packages = json.loads(packages_json)

        print("=== Conan Package Upload (Private Development Mode) ===")
        print("The following packages would be uploaded in production:")
        
        for package, details in packages["Local Cache"].items():
            package_recipes = []

            if "revisions" in details:
                package_recipes = [f"{package}#{revision}" for revision in details["revisions"]]
            else:
                package_recipes = [package]

            for package in package_recipes:
                remote = "cura-private-conan2" if "@internal" in package else "cura-conan2"
                
                print(f"  📦 Package: {package}")
                print(f"  🎯 Target Remote: {remote}")
                
                if not args.dry_run:
                    print(f"  ⏭️  Skipping upload for private development")
                    # In private development, we skip the actual upload
                    # subprocess.run(["conan", "upload", package, "-r", remote, "-c"], check=True)
                else:
                    print(f"  🔍 Dry run - would upload to {remote}")
                print()
        
        print("✅ Package processing completed successfully")
        print("💡 Note: Actual uploads are disabled for private development")
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error processing packages: {e}")
        if e.stdout:
            print(f"stdout: {e.stdout.decode()}")
        if e.stderr:
            print(f"stderr: {e.stderr.decode()}")
        raise
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Upload the given local package(s) to the proper Cura conan repository (Private Development Mode)')
    parser.add_argument('package', type=str, help='Package name, fully specific or containing wildcards')
    parser.add_argument('--dry-run', action='store_true', help='Do not upload the package but just show what would happen')

    args = parser.parse_args()
    upload_conan_package(args)
