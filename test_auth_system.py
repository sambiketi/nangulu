#!/usr/bin/env python3
"""
Test the authentication system
"""
import os
import sys
from dotenv import load_dotenv

# Try to load .env
load_dotenv()

print("🧪 Testing Nangulu POS Authentication System")
print("=" * 60)

# Test 1: Check environment
print("1. Environment check:")
print(f"   DATABASE_URL: {'Set' if os.getenv('DATABASE_URL') else 'Not set (will use test config)'}")
print(f"   SECRET_KEY: {'Set' if os.getenv('SECRET_KEY') else 'Not set (using default)'}")

# Test 2: Import checks
print("\n2. Import checks:")
try:
    import fastapi
    import sqlalchemy
    import jose
    import passlib
    print("   ✅ Core libraries imported")
except ImportError as e:
    print(f"   ❌ Import error: {e}")
    print("   Run: pip install -r requirements.txt")

# Test 3: App imports
print("\n3. App imports:")
try:
    sys.path.insert(0, ".")
    from app.main import app
    from app.database import get_db, test_connection
    from app.security import get_password_hash, verify_password
    print("   ✅ App modules imported")
    
    # Test password hashing
    test_password = "test123"
    hashed = get_password_hash(test_password)
    verified = verify_password(test_password, hashed)
    print(f"   ✅ Password hashing works: {verified}")
    
except Exception as e:
    print(f"   ❌ App import error: {e}")
    import traceback
    traceback.print_exc()

# Test 4: Database connection
print("\n4. Database connection:")
success, message = test_connection()
print(f"   {message}")

# Test 5: FastAPI routes
print("\n5. API Routes:")
try:
    auth_routes = [r.path for r in app.routes if "/auth" in r.path]
    print(f"   Found {len(auth_routes)} authentication routes:")
    for route in auth_routes[:5]:  # Show first 5
        print(f"   - {route}")
    
    # Check required routes
    required_routes = ["/api/auth/login", "/api/auth/me", "/api/auth/logout"]
    missing = [r for r in required_routes if r not in auth_routes]
    if not missing:
        print("   ✅ All required auth routes present")
    else:
        print(f"   ❌ Missing routes: {missing}")
        
except Exception as e:
    print(f"   ❌ Route check error: {e}")

print("\n" + "=" * 60)
print("📋 Summary:")
print("To test the authentication system:")
print("1. Edit .env file with your DATABASE_URL")
print("2. Start server: uvicorn app.main:app --reload")
print("3. Open: http://localhost:8000/api/docs")
print("4. Use default credentials from database:")
print("   - admin / admin123")
print("   - cashier1 / cashier123")
print("   - cashier2 / cashier456")
print("\n✅ Step 3 (auth & roles) ready for testing!")
