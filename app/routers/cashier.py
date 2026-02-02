from fastapi import APIRouter, Depends, HTTPException, Request, Form
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from app.models import Sale, InventoryItem, InventoryLedger, User
from app.dependencies import get_db, get_current_cashier
from decimal import Decimal, ROUND_UP
import uuid
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

templates = Jinja2Templates(directory="app/static/templates")
router = APIRouter()


# -----------------------------
# Request schema
# -----------------------------
class SaleCreate(BaseModel):
    item_id: int
    kg_sold: float
    payment_type: str = "Cash"
    customer_name: str | None = None


# -----------------------------
# Cashier login
# -----------------------------
@router.post("/login")
def cashier_login(...):
    print("=" * 50)
    print("DEBUG: cashier_login called")
    print(f"DEBUG: username param: {username}")
    print(f"DEBUG: password param: {password}")
    print("=" * 50)
    # ... rest of function
@router.post("/login")
def cashier_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.username == username, User.role == "cashier").first()
    if not user:
        request.session["error"] = "Invalid username"
        return RedirectResponse("/", status_code=302)

    import bcrypt
    if not bcrypt.checkpw(password.encode("utf-8"), user.password_hash):
        request.session["error"] = "Invalid password"
        return RedirectResponse("/", status_code=302)

    request.session["user_id"] = user.id
    request.session["role"] = user.role
    return RedirectResponse("/api/cashier/dashboard", status_code=302)


# -----------------------------
# Cashier dashboard
# -----------------------------
@router.get("/dashboard")
def cashier_dashboard(request: Request, db: Session = Depends(get_db), cashier: User = Depends(get_current_cashier)):
    inventory = db.query(InventoryItem).filter(InventoryItem.is_active == True).all()
    sales = (
        db.query(Sale)
        .filter(Sale.cashier_id == cashier.id)
        .order_by(Sale.created_at.desc())
        .limit(20)
        .all()
    )
    return templates.TemplateResponse(
        "cashier_dashboard.html",
        {
            "request": request,
            "inventory": inventory,
            "sales": sales,
            "cashier_name": cashier.full_name
        }
    )


# -----------------------------
# Confirm sale
# -----------------------------
@router.post("/sales")
def confirm_sale(
    sale: SaleCreate,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    item = db.query(InventoryItem).filter(
        InventoryItem.id == sale.item_id,
        InventoryItem.is_active == True
    ).first()

    if not item:
        raise HTTPException(404, "Item not found")
    if sale.kg_sold <= 0:
        raise HTTPException(400, "Invalid kg sold")
    if sale.kg_sold > float(item.quantity_available):
        raise HTTPException(400, "Not enough stock")

    total_price = (Decimal(item.current_price_per_kg) * Decimal(sale.kg_sold)).quantize(0, ROUND_UP)
    sale_number = str(uuid.uuid4())[:8].upper()

    sale_record = Sale(
        sale_number=sale_number,
        item_id=item.id,
        kg_sold=sale.kg_sold,
        price_per_kg_snapshot=item.current_price_per_kg,
        total_price=total_price,
        cashier_id=cashier.id,
        customer_name=sale.customer_name,
        status="ACTIVE"
    )
    db.add(sale_record)

    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=-sale.kg_sold,
        source_type="SALE",
        source_id=None,
        created_by=cashier.id,
        notes=f"Sold via {sale.payment_type}"
    )
    db.add(ledger)

    item.quantity_available -= sale.kg_sold
    db.commit()
    db.refresh(sale_record)

    return {
        "id": sale_record.id,
        "sale_number": sale_record.sale_number,
        "total_price": float(total_price),
        "item_name": item.name,
        "kg_sold": sale_record.kg_sold,
        "created_at": sale_record.created_at
    }


# -----------------------------
# Reverse sale
# -----------------------------
@router.post("/sales/{sale_id}/reverse")
def reverse_sale(sale_id: int, db: Session = Depends(get_db), cashier: User = Depends(get_current_cashier)):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.status == "ACTIVE").first()
    if not sale:
        raise HTTPException(404, "Sale not found or already reversed")

    sale.status = "REVERSED"
    item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
    if item:
        item.quantity_available += sale.kg_sold

    ledger = InventoryLedger(
        item_id=sale.item_id,
        kg_change=sale.kg_sold,
        source_type="SALE_REVERSAL",
        source_id=sale.id,
        created_by=cashier.id,
        notes=f"Sale reversed: {sale.sale_number}"
    )
    db.add(ledger)
    db.commit()
    db.refresh(sale)

    return {
        "id": sale.id,
        "sale_number": sale.sale_number,
        "status": sale.status
    }


# -----------------------------
# Recent sales for JS
# -----------------------------
@router.get("/sales/recent")
def recent_sales(db: Session = Depends(get_db), cashier: User = Depends(get_current_cashier)):
    sales = (
        db.query(Sale)
        .filter(Sale.cashier_id == cashier.id)
        .order_by(Sale.created_at.desc())
        .limit(20)
        .all()
    )
    return [
        {
            "id": sale.id,
            "sale_number": sale.sale_number,
            "item_name": sale.item.name if sale.item else "N/A",
            "kg_sold": sale.kg_sold,
            "total_price": float(sale.total_price),
            "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for sale in sales
    ]
