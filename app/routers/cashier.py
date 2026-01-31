from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from sqlalchemy.orm import Session
from app.models import Sale, InventoryItem, InventoryLedger
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
def cashier_dashboard(request: Request, db: Session = Depends(get_db)):
    # Get user role from session
    role = request.session.get("role")

    # Allow access only to cashiers
    if role != "cashier":
        return RedirectResponse("/", status_code=302)

    # Load inventory for selling
    inventory = db.query(InventoryItem).all()

    # Load sales history
    sales = db.query(Sale).all()

    # Render cashier dashboard
    return templates.TemplateResponse(
        "cashier_dashboard.html",
        {
            "request": request,
            "inventory": inventory,
            "sales": sales
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
    cashier=Depends(get_current_cashier)
):

    item = db.query(InventoryItem).get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    if kg_sold <= 0:
        raise HTTPException(400, "Invalid kg sold")

    # Round total price UP
    total_price = (Decimal(item.current_price_per_kg) * Decimal(kg_sold)).quantize(0, ROUND_UP)

    # Create Sale
    sale_number = str(uuid.uuid4())[:8].upper()
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

    # Update inventory ledger
    ledger = InventoryLedger(
        item_id=item.id,
        kg_change=-kg_sold,
        source_type="SALE",
        created_by=cashier.id,
        notes=f"Sold via {payment_type}"
    )
    db.add(ledger)
    db.commit()
    db.refresh(sale)
    return {"id": sale.id, "sale_number": sale.sale_number, "total_price": float(total_price)}

# -----------------------------
# Reverse sale
# -----------------------------
@router.post("/sales/{sale_id}/reverse")
def reverse_sale(sale_id: int, db: Session = Depends(get_db), cashier=Depends(get_current_cashier)):
    sale = db.query(Sale).get(sale_id)
    if not sale or sale.status != "ACTIVE":
