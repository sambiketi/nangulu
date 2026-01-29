#!/usr/bin/env python3
"""
Test all dependencies for Render compatibility
"""
import sys
import subprocess
import pkg_resources

def test_import(package_name, import_name=None):
    """Test if a package can be imported"""
    import_name = import_name or package_name.replace("-", "_")
    try:
        __import__(import_name)
        return True, f"✅ {package_name}"
    except ImportError as e:
        return False, f"❌ {package_name}: {str(e)}"

def check_package_version(package_name, min_version=None):
    """Check if package is installed and meets version requirement"""
    try:
        version = pkg_resources.get_distribution(package_name).version
        if min_version:
            if pkg_resources.parse_version(version) >= pkg_resources.parse_version(min_version):
                return True, f"✅ {package_name}=={version} (>= {min_version})"
            else:
                return False, f"⚠️ {package_name}=={version} (needs >= {min_version})"
        return True, f"✅ {package_name}=={version}"
    except pkg_resources.DistributionNotFound:
        return False, f"❌ {package_name} not installed"

def main():
    print("🔍 Testing Nangulu POS Dependencies for Render...")
    print("=" * 60)
    
    # Python version check
    python_version = sys.version.split()[0]
    print(f"Python version: {python_version}")
    
    # Required packages for Render
    packages = [
        ("fastapi", "0.104.1"),
        ("uvicorn", "0.24.0"),
        ("gunicorn", "21.2.0"),
        ("sqlalchemy", "2.0.25"),
        ("psycopg2-binary", "2.9.9"),
        ("pydantic", "2.5.3"),
        ("pydantic-settings", "2.1.0"),
        ("python-jose", "3.3.0"),
        ("passlib", "1.7.4"),
        ("python-multipart", "0.0.6"),
        ("python-dotenv", "1.0.0"),
        ("typing-extensions", "4.8.0"),
        ("anyio", "3.7.1"),
    ]
    
    all_passed = True
    
    print("\n📦 Package Version Checks:")
    for package, min_version in packages:
        passed, message = check_package_version(package, min_version)
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    print("\n🔧 Import Tests:")
    import_tests = [
        ("fastapi", "fastapi"),
        ("sqlalchemy", "sqlalchemy"),
        ("sqlalchemy.orm", "sqlalchemy.orm"),
        ("pydantic", "pydantic"),
        ("psycopg2", "psycopg2"),
        ("jose", "jose"),
        ("passlib", "passlib"),
    ]
    
    for package, import_name in import_tests:
        passed, message = test_import(package, import_name)
        print(f"  {message}")
        if not passed:
            all_passed = False
    
    # Test database connection if DATABASE_URL is set
    print("\n🗄️ Database Connection Test:")
    import os
    from dotenv import load_dotenv
    load_dotenv()
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if DATABASE_URL:
        try:
            from sqlalchemy import create_engine, text
            engine = create_engine(DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print("  ✅ Database connection successful")
        except Exception as e:
            print(f"  ❌ Database connection failed: {e}")
            all_passed = False
    else:
        print("  ⚠️ DATABASE_URL not set (set in .env file)")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All dependency checks passed! Ready for Render deployment.")
        print("\nNext steps:")
        print("1. git add . && git commit -m 'Initial POS system'")
        print("2. git push origin main")
        print("3. Deploy to Render: https://render.com")
    else:
        print("⚠️ Some checks failed. Please fix before deploying to Render.")
        sys.exit(1)

if __name__ == "__main__":
    main()
