#!/usr/bin/env python3
"""
Verify project structure matches README contract
"""
import os
import sys

REQUIRED_FILES = [
    "requirements.txt",
    "runtime.txt",
    "app/main.py",
    "app/database.py",
    "app/models.py",
    "app/schemas.py",
    "app/__init__.py",
    "app/routers/__init__.py",
    "app/routers/admin.py",
    "app/routers/cashier.py",
    "app/routers/auth.py",
    ".env.example",
    "setup.sh",
    "run.sh",
    "render.yaml",
]

REQUIRED_DIRS = [
    "app",
    "app/routers",
    "app/models",
    "app/crud",
    "app/schemas",
    "app/utils",
    "static/css",
    "static/js",
    "templates",
]

def check_file_exists(path):
    if os.path.exists(path):
        return True, f"✅ {path}"
    else:
        return False, f"❌ {path} (missing)"

def check_directory_exists(path):
    if os.path.isdir(path):
        return True, f"✅ {path}/"
    else:
        return False, f"❌ {path}/ (missing)"

def main():
    print("🔍 Verifying Nangulu POS Structure...")
    print("=" * 60)
    
    all_passed = True
    
    print("\n📁 Directory Structure:")
    for directory in REQUIRED_DIRS:
        passed, message = check_directory_exists(directory)
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    print("\n📄 Required Files:")
    for file in REQUIRED_FILES:
        passed, message = check_file_exists(file)
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    # Check requirements.txt content
    print("\n📦 requirements.txt check:")
    if os.path.exists("requirements.txt"):
        with open("requirements.txt", "r") as f:
            content = f.read()
            lines = [line.strip() for line in content.split('\n') if line.strip()]
            print(f"  Found {len(lines)} dependencies")
            
            # Check for critical packages
            critical = ["fastapi", "sqlalchemy", "psycopg2", "pydantic"]
            for package in critical:
                if any(package in line.lower() for line in lines):
                    print(f"  ✅ {package} in requirements.txt")
                else:
                    print(f"  ❌ {package} missing from requirements.txt")
                    all_passed = False
    else:
        print("  ❌ requirements.txt not found")
        all_passed = False
    
    # Check runtime.txt
    print("\n🐍 runtime.txt check:")
    if os.path.exists("runtime.txt"):
        with open("runtime.txt", "r") as f:
            version = f.read().strip()
            if "3.11" in version:
                print(f"  ✅ Python 3.11 specified: {version}")
            else:
                print(f"  ⚠️ Not Python 3.11: {version}")
                print("  Note: Python 3.11 has best wheel support for Render")
    else:
        print("  ⚠️ runtime.txt not found (optional but recommended)")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 Structure verification complete! All checks passed.")
        print("\nTo test the application locally:")
        print("  ./setup.sh  # Install dependencies")
        print("  ./run.sh    # Start the server")
        print("\nTo deploy to Render:")
        print("  1. Push to GitHub")
        print("  2. Connect repository in Render dashboard")
        print("  3. Render will use render.yaml automatically")
    else:
        print("⚠️ Structure verification failed. Missing required files/directories.")
        sys.exit(1)

if __name__ == "__main__":
    main()
