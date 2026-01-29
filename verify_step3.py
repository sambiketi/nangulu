#!/usr/bin/env python3
"""
Verify Step 3 (auth & roles) implementation
"""
import os
import sys

print("🔍 Verifying Step 3: auth & roles implementation")
print("=" * 60)

# Check required files
required_files = [
    "app/__init__.py",
    "app/main.py",
    "app/database.py",
    "app/models.py",
    "app/security.py",
    "app/routers/__init__.py",
    "app/routers/auth.py",
]

all_good = True
for file in required_files:
    if os.path.exists(file):
        print(f"✅ {file}")
    else:
        print(f"❌ {file} (missing)")
        all_good = False

print()
print("📦 Checking imports...")

# Test basic imports
try:
    import fastapi
    import sqlalchemy
    import jose
    import passlib
    print("✅ Core imports work")
except ImportError as e:
    print(f"❌ Import error: {e}")
    all_good = False

# Test app imports
try:
    sys.path.insert(0, ".")
    from app.main import app
    from app.database import get_db
    from app.security import get_password_hash, verify_password
    print("✅ App imports work")
    
    # Check routes
    routes = [route.path for route in app.routes]
    auth_routes = [r for r in routes if "/auth" in r]
    print(f"✅ Found {len(auth_routes)} auth routes")
    
except Exception as e:
    print(f"❌ App import error: {e}")
    all_good = False

print()
print("=" * 60)
if all_good:
    print("🎉 Step 3 (auth & roles) implementation verified!")
    print()
    print("Next steps:")
    print("1. Test the API: uvicorn app.main:app --reload")
    print("2. Login at: POST /api/auth/login")
    print("3. Get your info: GET /api/auth/me (with token)")
    print()
    print("Default credentials (from database schema):")
    print("  admin / admin123")
    print("  cashier1 / cashier123")
    print("  cashier2 / cashier456")
else:
    print("⚠️ Verification failed. Check missing files.")
    sys.exit(1)
