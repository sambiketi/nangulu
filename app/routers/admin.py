from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session

from app.models import User, InventoryItem, InventoryLedger
from app.schemas import UserCreate
from app.dependencies import get_db, get_current_admin, get_password_hash

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/static/templates")

router = APIRouter()

# -----------------------------
# Admin dashboard route
# -----------------------------
@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    # Get user role from session
    role = request.session.get("role")

    # Allow access only to admins
    if role != "admin":
        return RedirectResponse("/", status_code=302)

    # Load all cashiers
    cashiers = db.query(User).all()

    # Load inventory data
    inventory = db.query(InventoryItem).all()

    # Render admin dashboard
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
def create_cashier(user: UserCreate, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
    if user.role != "cashier":
        raise HTTPException(400, "Role must be cashier")
    if db.query(User).filter(User.username == user.username).first():
        raise HTTPException(400, "Username exists")
    hashed_password = get_password_hash(user.password)
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
# Deactivate cashier (data stays)
# -----------------------------
@router.delete("/cashiers/{cashier_id}")
def deactivate_cashier(cashier_id: int, db: Session = Depends(get_db), admin=Depends(get_current_admin)):
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
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
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
        created_by=admin.id,
        notes=f"Purchase added by admin {admin.username}"
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
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin)
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
import csv
from fastapi.responses import StreamingResponse
from io import StringIO
from datetime import datetime

@router.get("/ledger/download")
def download_ledger(db: Session = Depends(get_db), admin=Depends(get_current_admin)):
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
