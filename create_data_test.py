from app.database import SessionLocal, engine
from app.models import Base, User
from app.dependencies import get_password_hash
import sqlite3

# Create tables if they don't exist
Base.metadata.create_all(bind=engine)

db = SessionLocal()

# Check if admin user exists
admin = db.query(User).filter(User.username == "admin").first()
if not admin:
    # Create admin user
    admin_user = User(
        username="admin",
        password_hash=get_password_hash("admin123"),
        full_name="System Administrator",
        role="admin",
        is_active=True
    )
    db.add(admin_user)
    print("✅ Created admin user: admin / admin123")

# Check if cashier users exist
cashier1 = db.query(User).filter(User.username == "cashier1").first()
if not cashier1:
    cashier1_user = User(
        username="cashier1",
        password_hash=get_password_hash("cashier123"),
        full_name="Cashier One",
        role="cashier",
        is_active=True
    )
    db.add(cashier1_user)
    print("✅ Created cashier1 user: cashier1 / cashier123")

cashier2 = db.query(User).filter(User.username == "cashier2").first()
if not cashier2:
    cashier2_user = User(
        username="cashier2",
        password_hash=get_password_hash("cashier123"),
        full_name="Cashier Two",
        role="cashier",
        is_active=True
    )
    db.add(cashier2_user)
    print("✅ Created cashier2 user: cashier2 / cashier123")

db.commit()
db.close()

print("\n✅ Test users created successfully!")
print("\nLogin credentials:")
print("Admin:    admin / admin123")
print("Cashier1: cashier1 / cashier123")
print("Cashier2: cashier2 / cashier123")