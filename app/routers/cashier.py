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
# In-memory cashiers for testing (plain text passwords)
IN_MEMORY_CASHIERS = {
    "cashier1": {
        "id": 2,  
        "username": "cashier1",
        "password": "cashier123",  # Plain text
        "role": "cashier",
        "is_active": True,
        "full_name": "Cashier One"
    },
    "cashier2": {
        "id": 3,
        "username": "cashier2", 
        "password": "cashier123",  # Plain text
        "role": "cashier",
        "is_active": True,
        "full_name": "Cashier Two"
    }
}

# -----------------------------
# Request schema
# -----------------------------
class SaleCreate(BaseModel):
    item_id: int
    kg_sold: float
    payment_type: str = "Cash"
    customer_name: str | None = None


# -----------------------------
#@router.post("/login")
def cashier_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # First check in-memory cashiers
    if username in IN_MEMORY_CASHIERS:
        cashier = IN_MEMORY_CASHIERS[username]
        if password == cashier["password"]:  # Plain text comparison
            request.session["user_id"] = cashier["id"]
            request.session["role"] = cashier["role"]
            return RedirectResponse("/api/cashier/dashboard", status_code=302)
        else:
            request.session["error"] = "Invalid password"
            return RedirectResponse("/", status_code=302)
    
    # If not in memory, check database
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
# Complete sale with proper Decimal handling
# -----------------------------
@router.post("/sales")
def complete_sale(
    sale: SaleCreate,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    # Get item from inventory
    item = db.query(InventoryItem).filter(
        InventoryItem.id == sale.item_id,
        InventoryItem.is_active == True
    ).first()

    if not item:
        raise HTTPException(404, "Item not found")
    
    # Convert kg_sold to Decimal for consistent operations
    kg_sold_decimal = Decimal(str(sale.kg_sold)).quantize(Decimal('0.001'))
    
    # Validate kg_sold
    if kg_sold_decimal <= Decimal('0'):
        raise HTTPException(400, "Invalid kg sold")
    
    # Check stock availability (Decimal comparison)
    if kg_sold_decimal > item.quantity_available:
        raise HTTPException(400, "Not enough stock")

    # Calculate total price
    total_price = (item.current_price_per_kg * kg_sold_decimal).quantize(Decimal('0.00'), ROUND_UP)
    sale_number = str(uuid.uuid4())[:8].upper()

    # Create sale record
    sale_record = Sale(
        sale_number=sale_number,
        item_id=item.id,
        kg_sold=kg_sold_decimal,  # Use Decimal
        price_per_kg_snapshot=item.current_price_per_kg,
        total_price=total_price,
        cashier_id=cashier.id,
        payment_type=sale.payment_type,
        customer_name=sale.customer_name,
        status="ACTIVE"
    )
    db.add(sale_record)

    # Create inventory ledger entry
    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=-kg_sold_decimal,  # Use Decimal
        source_type="SALE",
        source_id=None,
        created_by=cashier.id,
        notes=f"Sold via {sale.payment_type}"
    )
    db.add(ledger)

    # Update inventory stock (Decimal operation)
    item.quantity_available -= kg_sold_decimal
    
    # Commit all changes
    db.commit()
    db.refresh(sale_record)

    return {
        "id": sale_record.id,
        "sale_number": sale_record.sale_number,
        "total_price": float(total_price),
        "item_name": item.name,
        "kg_sold": float(kg_sold_decimal),
        "created_at": sale_record.created_at.strftime("%Y-%m-%d %H:%M:%S")
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
        # Add back the kg_sold (already Decimal in sale record)
        item.quantity_available += sale.kg_sold

    ledger = InventoryLedger(
        item_id=sale.item_id,
        kg_change=sale.kg_sold,  # Positive change for reversal
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
            "kg_sold": float(sale.kg_sold),
            "total_price": float(sale.total_price),
            "created_at": sale.created_at.strftime("%Y-%m-%d %H:%M:%S")
        }
        for sale in sales
    ]