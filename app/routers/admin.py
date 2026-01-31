from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session
from io import StringIO
import csv
from datetime import datetime
import bcrypt

from app.models import User, InventoryItem, InventoryLedger
from app.schemas import UserCreate
from app.dependencies import get_db
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/static/templates")
router = APIRouter()

# -----------------------------
# In-memory admin with lazy password hashing
# -----------------------------
ADMIN_USER = {
    "id": 0,
    "username": "admin",
    "_password_plain": "admin123",  # store plain temporarily
    "password_hash": None,          # hashed on first use
    "role": "admin",
    "is_active": True,
    "full_name": "Super Admin"
}

def get_admin_password_hash():
    """Compute and cache admin password hash on first use."""
    if ADMIN_USER["password_hash"] is None:
        # bcrypt max 72 bytes
        ADMIN_USER["password_hash"] = bcrypt.hashpw(
            ADMIN_USER["_password_plain"].encode('utf-8')[:72],
            bcrypt.gensalt()
        )
    return ADMIN_USER["password_hash"]

# -----------------------------
# Admin dashboard route
# -----------------------------
@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    role = request.session.get("role")
    user_id = request.session.get("user_id")

    # Only allow the in-memory admin
    if role != "admin" or user_id != ADMIN_USER["id"]:
        return RedirectResponse("/", status_code=302)

    # Load all cashiers from DB
    cashiers = db.query(User).filter(User.role == "cashier").all()

    # Load inventory data
    inventory = db.query(InventoryItem).all()

    # Render template
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "cashiers": cashiers,
            "inventory": inventory
        }
    )

# -----------------------------
# Create new cashier
# -----------------------------
@router.post("/cashiers")
def create_cashier(user: UserCreate, db: Session = Depends(get_db)):
    if user.role != "cashier":
        raise HTTPException(400, "Role must be cashier")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(400, "Username exists")
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8')[:72], bcrypt.gensalt())
    new_user = User(
        username=user.username,
        full_name=user.full_name,
        role="cashier",
        password_hash=hashed_password
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username}

# -----------------------------
# Deactivate cashier
# -----------------------------
@router.delete("/cashiers/{cashier_id}")
def deactivate_cashier(cashier_id: int, db: Session = Depends(get_db)):
    user = db.query(User).get(cashier_id)
    if not user or user.role != "cashier":
        raise HTTPException(404, "Cashier not found")
    user.is_active = False
    db.commit()
    return {"id": user.id, "username": user.username}

# -----------------------------
# Add purchase / add stock
# -----------------------------
@router.post("/purchases")
def add_purchase(
    item_id: int = None,
    name: str = None,
    description: str = None,
    kg_added: float = None,
    purchase_price_per_kg: float = None,
    db: Session = Depends(get_db)
):
    if kg_added <= 0 or purchase_price_per_kg <= 0:
        raise HTTPException(400, "Invalid kg or price")

    if item_id:
        item = db.query(InventoryItem).get(item_id)
        if not item:
            raise HTTPException(404, "Item not found")
        item.current_price_per_kg = purchase_price_per_kg
        db.add(item)
    else:
        item = InventoryItem(
            name=name,
            description=description,
            current_price_per_kg=purchase_price_per_kg
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=kg_added,
        source_type="PURCHASE",
        created_by=ADMIN_USER["id"],
        notes=f"Purchase added by admin {ADMIN_USER['username']}"
    )
    db.add(ledger)
    db.commit()
    db.refresh(ledger)
    return {"id": ledger.id, "item_id": item.id}

# -----------------------------
# Set selling price
# -----------------------------
@router.patch("/inventory/{item_id}/price")
def set_selling_price(
    item_id: int,
    price: float = Query(..., gt=0),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    item.current_price_per_kg = price
    db.commit()
    return {"id": item.id, "new_price": item.current_price_per_kg}

# -----------------------------
# Download Inventory Ledger
# -----------------------------
@router.get("/ledger/download")
def download_ledger(db: Session = Depends(get_db)):
    ledger_entries = db.query(InventoryLedger).order_by(
        InventoryLedger.created_at.desc()
    ).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "Item ID", "Kg Change", "Source Type", "Source ID", "Notes", "Created By", "Created At"]
    )

    for entry in ledger_entries:
        writer.writerow([
            entry.id,
            entry.item_id,
            float(entry.kg_change),
            entry.source_type,
            entry.source_id or "",
            entry.notes,
            entry.created_by,
            entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
        ])

    output.seek(0)
    filename = f"ledger_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
