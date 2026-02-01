from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.models import Sale, InventoryItem, InventoryLedger, User
from app.dependencies import get_db, get_current_cashier
from decimal import Decimal, ROUND_UP
import uuid
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/static/templates")

router = APIRouter()


# -----------------------------
# Cashier dashboard route
# -----------------------------
@router.get("/dashboard")
def cashier_dashboard(request: Request, db: Session = Depends(get_db), cashier: User = Depends(get_current_cashier)):
    """
    Load cashier dashboard:
    - Inventory for selling
    - Recent sales for this cashier
    """
    # Role check (redundant if get_current_cashier works)
    if cashier.role != "cashier":
        return RedirectResponse("/", status_code=302)

    # Load inventory for selling
    inventory = db.query(InventoryItem).filter(InventoryItem.is_active == True).all()

    # Load recent sales for this cashier
    sales = db.query(Sale).filter(Sale.cashier_id == cashier.id).order_by(Sale.created_at.desc()).limit(20).all()

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
    item_id: int,
    kg_sold: float,
    payment_type: str = "Cash",
    customer_name: str = None,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Confirm a new sale:
    - Validates inventory
    - Rounds total price UP
    - Creates Sale record
    - Updates Inventory Ledger
    """
    item = db.query(InventoryItem).filter(InventoryItem.id == item_id, InventoryItem.is_active == True).first()
    if not item:
        raise HTTPException(404, "Item not found")

    if kg_sold <= 0:
        raise HTTPException(400, "Invalid kg sold")

    if kg_sold > float(item.quantity_available):
        raise HTTPException(400, "Not enough stock")

    # Round total price UP
    total_price = (Decimal(item.current_price_per_kg) * Decimal(kg_sold)).quantize(0, ROUND_UP)

    # Auto-generate sale number
    sale_number = str(uuid.uuid4())[:8].upper()

    # Create Sale
    sale = Sale(
        sale_number=sale_number,
        item_id=item.id,
        kg_sold=kg_sold,
        price_per_kg_snapshot=item.current_price_per_kg,
        total_price=total_price,
        cashier_id=cashier.id,
        customer_name=customer_name,
        status="ACTIVE"
    )
    db.add(sale)

    # Deduct stock in ledger
    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=-kg_sold,
        source_type="SALE",
        source_id=None,
        created_by=cashier.id,
        notes=f"Sold via {payment_type}"
    )
    db.add(ledger)

    # Update actual inventory quantity
    item.quantity_available -= kg_sold

    db.commit()
    db.refresh(sale)

    return {
        "id": sale.id,
        "sale_number": sale.sale_number,
        "total_price": float(total_price),
        "item_name": item.name,
        "kg_sold": sale.kg_sold,
        "created_at": sale.created_at
    }


# -----------------------------
# Reverse sale
# -----------------------------
@router.post("/sales/{sale_id}/reverse")
def reverse_sale(sale_id: int, db: Session = Depends(get_db), cashier: User = Depends(get_current_cashier)):
    """
    Reverse a sale:
    - Updates sale status
    - Returns kg to inventory
    - Creates ledger entry
    """
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.status == "ACTIVE").first()
    if not sale:
        raise HTTPException(404, "Sale not found or already reversed")

    sale.status = "REVERSED"

    # Return kg to inventory
    item = db.query(InventoryItem).filter(InventoryItem.id == sale.item_id).first()
    if item:
        item.quantity_available += sale.kg_sold

    # Ledger entry for reversal
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
