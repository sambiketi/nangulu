"""
Inventory router for Step 4: inventory + ledger logic
Contract: Admin controls structure, ledger is append-only
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from decimal import Decimal

from app.database import get_db
from app.security import get_current_user, require_admin, audit_log_action
from app import models, schemas
from app.crud.inventory import crud_inventory_item, crud_inventory_ledger
from app.schemas.inventory import (
    InventoryItemCreate, InventoryItemResponse, InventoryItemUpdate,
    PurchaseCreate, StockStatusResponse, ConversionRequest, ConversionResponse,
    LedgerEntryResponse, SourceType
)

router = APIRouter(prefix="/inventory", tags=["inventory"])

# ====================
# INVENTORY ITEMS (Admin only)
# ====================

@router.post("/items", response_model=InventoryItemResponse)
async def create_inventory_item(
    item: InventoryItemCreate,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Create new inventory item (admin only)
    Contract: Admin controls structure
    """
    # Check if item name already exists
    existing = crud_inventory_item.get_by_name(db, name=item.name)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Inventory item with name '{item.name}' already exists"
        )
    
    # Create item
    db_item = crud_inventory_item.create_with_creator(
        db, obj_in=item, creator_id=current_user.id
    )
    
    if not db_item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create inventory item"
        )
    
    # Audit log
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="INVENTORY_ITEM_CREATE",
        table_name="inventory_items",
        record_id=db_item.id,
        new_values={
            "name": db_item.name,
            "price_per_kg": float(db_item.current_price_per_kg),
            "low_stock": float(db_item.low_stock_level),
            "critical_stock": float(db_item.critical_stock_level)
        },
        notes=f"Admin {current_user.username} created inventory item {db_item.name}"
    )
    
    return db_item

@router.get("/items", response_model=List[InventoryItemResponse])
async def list_inventory_items(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List inventory items (all authenticated users)
    Contract: Cashiers see items, admin sees all
    """
    items = crud_inventory_item.get_active_items(db, skip=skip, limit=limit)
    return items

@router.get("/items/{item_id}", response_model=InventoryItemResponse)
async def get_inventory_item(
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get specific inventory item
    """
    item = crud_inventory_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    if not item.is_active and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive inventory item"
        )
    
    return item

@router.put("/items/{item_id}/price")
async def update_item_price(
    item_id: int,
    new_price: Decimal,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Update item price per kg (admin only)
    Contract: Price changes affect future sales only
    """
    item = crud_inventory_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    old_price = item.current_price_per_kg
    updated_item = crud_inventory_item.update_price(
        db, id=item_id, new_price=new_price, updated_by=current_user.id
    )
    
    if not updated_item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update item price"
        )
    
    # Audit log
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="INVENTORY_PRICE_UPDATE",
        table_name="inventory_items",
        record_id=item_id,
        old_values={"price_per_kg": float(old_price)},
        new_values={"price_per_kg": float(new_price)},
        notes=f"Admin {current_user.username} updated price for {item.name} from {old_price} to {new_price}"
    )
    
    return {
        "message": "Price updated successfully",
        "item": updated_item,
        "old_price": old_price,
        "new_price": new_price
    }

# ====================
# STOCK OPERATIONS
# ====================

@router.post("/purchases", response_model=dict)
async def create_purchase(
    purchase: PurchaseCreate,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Record stock purchase (admin only)
    Contract: Items created when admin records purchase
    """
    ledger_entry, item = crud_inventory_ledger.create_purchase_entry(
        db, purchase_data=purchase, user_id=current_user.id
    )
    
    if not ledger_entry or not item:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record purchase"
        )
    
    # Calculate new stock
    new_stock = crud_inventory_ledger.get_item_stock(db, item.id)
    
    # Audit log
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="STOCK_PURCHASE",
        table_name="inventory_ledger",
        record_id=ledger_entry.id,
        new_values={
            "item_id": item.id,
            "item_name": item.name,
            "kg_purchased": float(purchase.purchase_kg),
            "cost_per_kg": float(purchase.cost_per_kg),
            "total_cost": float(purchase.purchase_kg * purchase.cost_per_kg),
            "new_stock": float(new_stock)
        },
        notes=f"Admin {current_user.username} purchased {purchase.purchase_kg}kg of {item.name}"
    )
    
    return {
        "message": "Purchase recorded successfully",
        "ledger_entry_id": ledger_entry.id,
        "item": item,
        "new_stock": new_stock,
        "purchase_details": {
            "kg": purchase.purchase_kg,
            "cost_per_kg": purchase.cost_per_kg,
            "total_cost": purchase.purchase_kg * purchase.cost_per_kg,
            "supplier": purchase.supplier_name
        }
    }

@router.get("/items/{item_id}/stock")
async def get_item_stock(
    item_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current stock for item
    Contract: KGs as source of truth
    """
    item = crud_inventory_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    if not item.is_active and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive inventory item"
        )
    
    stock = crud_inventory_ledger.get_item_stock(db, item_id)
    
    # Determine stock status
    stock_status = "NORMAL"
    if stock <= item.critical_stock_level:
        stock_status = "CRITICAL"
    elif stock <= item.low_stock_level:
        stock_status = "LOW"
    
    stock_value = stock * item.current_price_per_kg
    
    return StockStatusResponse(
        item_id=item.id,
        name=item.name,
        total_kg=stock,
        current_price_per_kg=item.current_price_per_kg,
        low_stock_level=item.low_stock_level,
        critical_stock_level=item.critical_stock_level,
        stock_status=stock_status,
        stock_value=stock_value
    )

@router.get("/stock-status", response_model=List[StockStatusResponse])
async def get_all_stock_status(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get stock status for all active items
    Contract: Low/critical stock alerts
    """
    items = crud_inventory_item.get_active_items(db, skip=0, limit=1000)
    
    stock_status_list = []
    for item in items:
        stock = crud_inventory_ledger.get_item_stock(db, item.id)
        
        # Determine stock status
        stock_status = "NORMAL"
        if stock <= item.critical_stock_level:
            stock_status = "CRITICAL"
        elif stock <= item.low_stock_level:
            stock_status = "LOW"
        
        stock_value = stock * item.current_price_per_kg
        
        stock_status_list.append(StockStatusResponse(
            item_id=item.id,
            name=item.name,
            total_kg=stock,
            current_price_per_kg=item.current_price_per_kg,
            low_stock_level=item.low_stock_level,
            critical_stock_level=item.critical_stock_level,
            stock_status=stock_status,
            stock_value=stock_value
        ))
    
    return stock_status_list

# ====================
# LEDGER OPERATIONS
# ====================

@router.get("/items/{item_id}/ledger", response_model=List[LedgerEntryResponse])
async def get_item_ledger(
    item_id: int,
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get ledger entries for specific item
    Contract: Append-only ledger, full transparency
    """
    item = crud_inventory_item.get(db, id=item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    if not item.is_active and current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive inventory item"
        )
    
    ledger_entries = crud_inventory_ledger.get_item_ledger(db, item_id, skip=skip, limit=limit)
    
    # Add item name to responses
    response_entries = []
    for entry in ledger_entries:
        entry_dict = {**entry.__dict__}
        entry_dict["item_name"] = item.name
        response_entries.append(LedgerEntryResponse(**entry_dict))
    
    return response_entries

# ====================
# CONVERSION UTILITIES
# ====================

@router.post("/convert", response_model=ConversionResponse)
async def convert_kg_price(
    conversion: ConversionRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Convert between KG and Price
    Contract: Cashiers enter KG → auto-calculated price OR price → auto-calculated KG
    """
    item = crud_inventory_item.get(db, id=conversion.item_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Inventory item not found"
        )
    
    if not item.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inventory item is inactive"
        )
    
    if conversion.is_kg:
        # KG → Price conversion
        kg_amount = conversion.amount
        price_amount = kg_amount * item.current_price_per_kg
    else:
        # Price → KG conversion
        price_amount = conversion.amount
        kg_amount = price_amount / item.current_price_per_kg
        # Round to 3 decimal places (contract: KG precision)
        kg_amount = kg_amount.quantize(Decimal('0.001'))
    
    return ConversionResponse(
        item_id=item.id,
        item_name=item.name,
        kg_amount=kg_amount,
        price_amount=price_amount,
        current_price_per_kg=item.current_price_per_kg
    )

# ====================
# ADMIN DASHBOARD ENDPOINTS
# ====================

@router.get("/low-stock-alerts")
async def get_low_stock_alerts(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Get low and critical stock alerts (admin only)
    Contract: Alerts appear on admin dashboard
    """
    items = crud_inventory_item.get_active_items(db, skip=0, limit=1000)
    
    alerts = []
    for item in items:
        stock = crud_inventory_ledger.get_item_stock(db, item.id)
        
        if stock <= item.critical_stock_level:
            alert_level = "CRITICAL"
            alerts.append({
                "item_id": item.id,
                "name": item.name,
                "current_stock": float(stock),
                "threshold": float(item.critical_stock_level),
                "alert_level": alert_level,
                "urgency": "IMMEDIATE"
            })
        elif stock <= item.low_stock_level:
            alert_level = "LOW"
            alerts.append({
                "item_id": item.id,
                "name": item.name,
                "current_stock": float(stock),
                "threshold": float(item.low_stock_level),
                "alert_level": alert_level,
                "urgency": "SOON"
            })
    
    return {
        "alerts": alerts,
        "critical_count": len([a for a in alerts if a["alert_level"] == "CRITICAL"]),
        "low_count": len([a for a in alerts if a["alert_level"] == "LOW"]),
        "total_items": len(items)
    }

@router.get("/health/detailed")
async def detailed_inventory_health(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Detailed inventory health check (admin only)
    Contract: Shows on admin dashboard and health endpoint
    """
    items = crud_inventory_item.get_active_items(db, skip=0, limit=1000)
    
    total_stock_value = Decimal('0')
    low_stock_items = 0
    critical_stock_items = 0
    
    for item in items:
        stock = crud_inventory_ledger.get_item_stock(db, item.id)
        stock_value = stock * item.current_price_per_kg
        total_stock_value += stock_value
        
        if stock <= item.critical_stock_level:
            critical_stock_items += 1
        elif stock <= item.low_stock_level:
            low_stock_items += 1
    
    return {
        "total_items": len(items),
        "total_stock_value": float(total_stock_value),
        "low_stock_items": low_stock_items,
        "critical_stock_items": critical_stock_items,
        "health_status": "GOOD" if critical_stock_items == 0 else "WARNING"
    }
