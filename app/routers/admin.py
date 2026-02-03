from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy.orm import Session, joinedload  # FIX: Added joinedload
from io import StringIO
import csv
from datetime import datetime
import bcrypt
from decimal import Decimal
from pydantic import BaseModel

from app.models import User, InventoryItem, InventoryLedger, Sale
from app.schemas import UserCreate
from app.dependencies import get_db
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/static/templates")
router = APIRouter()

# -----------------------------
# Request schemas
# -----------------------------
class SetPriceRequest(BaseModel):
    current_price_per_kg: float

class AddStockRequest(BaseModel):
    item_id: int | None = None
    kg_added: float
    purchase_price_per_kg: float | None = None
    name: str | None = None
    description: str | None = None

# In-memory admin
ADMIN_USER = {
    "id": 0,
    "username": "admin",
    "_password_plain": "admin123",
    "password_hash": None,
    "role": "admin",
    "is_active": True,
    "full_name": "Super Admin"
}

def get_admin_password_hash():
    if ADMIN_USER["password_hash"] is None:
        ADMIN_USER["password_hash"] = bcrypt.hashpw(
            ADMIN_USER["_password_plain"].encode('utf-8')[:72],
            bcrypt.gensalt()
        )
    return ADMIN_USER["password_hash"]

# -----------------------------
# Admin dashboard - UPDATED to include sales
# -----------------------------
@router.get("/dashboard")
def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    role = request.session.get("role")
    user_id = request.session.get("user_id")

    if role != "admin" or user_id != ADMIN_USER["id"]:
        return RedirectResponse("/", status_code=302)

    cashiers = db.query(User).filter(User.role == "cashier").all()
    inventory = db.query(InventoryItem).all()
    
    # FIX: Load sales with relationships for template
    sales = db.query(Sale).options(
        joinedload(Sale.item),
        joinedload(Sale.cashier)
    ).order_by(Sale.created_at.desc()).limit(100).all()

    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "cashiers": cashiers,
            "inventory": inventory,
            "sales": sales  # FIX: Added sales data
        }
    )

# -----------------------------
# Admin login
# -----------------------------
@router.post("/login")
def login_admin(request: Request, username: str = Query(...), password: str = Query(...)):
    if username != ADMIN_USER["username"]:
        request.session["error"] = "Invalid admin username"
        return RedirectResponse("/", status_code=302)

    if not bcrypt.checkpw(password.encode('utf-8')[:72], get_admin_password_hash()):
        request.session["error"] = "Invalid admin password"
        return RedirectResponse("/", status_code=302)

    request.session["user_id"] = ADMIN_USER["id"]
    request.session["role"] = "admin"
    return RedirectResponse("/api/admin/dashboard", status_code=302)


# -----------------------------
# Cashier management
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
        password_hash=hashed_password,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return {"id": new_user.id, "username": new_user.username, "full_name": new_user.full_name}


@router.delete("/cashiers/{cashier_id}")
def deactivate_cashier(cashier_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == cashier_id, User.role == "cashier").first()
    if not user:
        raise HTTPException(404, "Cashier not found")
    user.is_active = False
    db.commit()
    return {"id": user.id, "username": user.username, "is_active": user.is_active}


# -----------------------------
# Inventory / Purchases
# -----------------------------
@router.post("/purchases")
def add_purchase(
    request: AddStockRequest,
    db: Session = Depends(get_db)
):
    if request.kg_added <= 0:
        raise HTTPException(400, "Invalid kg amount")
    
    if request.item_id:
        # Add stock to existing item
        item = db.query(InventoryItem).filter(InventoryItem.id == request.item_id).first()
        if not item:
            raise HTTPException(404, "Item not found")
        
        if request.purchase_price_per_kg:
            item.purchase_price_per_kg = Decimal(str(request.purchase_price_per_kg))
    else:
        # Create new item
        if not request.name:
            raise HTTPException(400, "Item name required for new items")
        
        item = InventoryItem(
            name=request.name,
            description=request.description or "",
            current_price_per_kg=Decimal(str(request.purchase_price_per_kg)) if request.purchase_price_per_kg else Decimal('0'),
            quantity_available=0,
            is_active=True
        )
        db.add(item)
        db.commit()
        db.refresh(item)

    # Create ledger entry
    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=Decimal(str(request.kg_added)),
        source_type="PURCHASE",
        source_id=None,
        created_by=ADMIN_USER["id"],
        notes=f"Purchase added by admin"
    )
    db.add(ledger)
    
    # Update quantity with Decimal
    item.quantity_available += Decimal(str(request.kg_added))
    db.commit()
    
    return {"id": ledger.id, "item_id": item.id, "kg_added": request.kg_added}


@router.patch("/inventory/{item_id}/price")
def set_selling_price(
    item_id: int, 
    request: SetPriceRequest,
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
    if not item:
        raise HTTPException(404, "Item not found")
    
    if request.current_price_per_kg <= 0:
        raise HTTPException(400, "Price must be greater than 0")
    
    item.current_price_per_kg = Decimal(str(request.current_price_per_kg))
    db.commit()
    return {"id": item.id, "new_price": float(item.current_price_per_kg)}


# -----------------------------
# Sales endpoints
# -----------------------------
@router.get("/sales/item/{item_id}")
def get_item_sales(item_id: int, db: Session = Depends(get_db)):
    sales = db.query(Sale).options(
        joinedload(Sale.item),
        joinedload(Sale.cashier)
    ).filter(Sale.item_id == item_id).order_by(Sale.created_at.desc()).all()
    
    return [
        {
            "sale_number": sale.sale_number,
            "item_name": sale.item.name if sale.item else "N/A",
            "kg_sold": float(sale.kg_sold),
            "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
            "total_price": float(sale.total_price),
            "cashier_name": sale.cashier.full_name if sale.cashier else "N/A",
            "customer_name": sale.customer_name or "-",
            "status": sale.status,
            "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for sale in sales
    ]


# FIX: Added endpoint for loading all sales (for JavaScript refresh)
@router.get("/sales/all")
def get_all_sales(db: Session = Depends(get_db)):
    sales = db.query(Sale).options(
        joinedload(Sale.item),
        joinedload(Sale.cashier)
    ).order_by(Sale.created_at.desc()).limit(200).all()
    
    return [
        {
            "sale_number": sale.sale_number,
            "item_name": sale.item.name if sale.item else "N/A",
            "kg_sold": float(sale.kg_sold),
            "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
            "total_price": float(sale.total_price),
            "cashier_name": sale.cashier.full_name if sale.cashier else "N/A",
            "customer_name": sale.customer_name or "-",
            "status": sale.status,
            "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for sale in sales
    ]


@router.get("/ledger/download")
def download_ledger(db: Session = Depends(get_db)):
    ledger_entries = db.query(InventoryLedger).order_by(InventoryLedger.created_at.desc()).all()

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