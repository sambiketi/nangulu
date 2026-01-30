"""
Cashier router for sales and reversals.
Cashier role required for all endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.auth import get_current_user
from app.models import User
from app.schemas.inventory import (
    SaleCreate, SaleResponse, SaleListResponse,
    SaleReversalCreate, SaleReversalResponse
)
from app.crud.inventory import crud_inventory_ledger as crud_ledger

router = APIRouter(prefix="/cashier", tags=["cashier"])

# Dependency to ensure user is cashier
def get_current_cashier(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Ensure user is an active cashier"""
    if current_user.role != "cashier":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashier role required"
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashier account is inactive"
        )
    
    return current_user

@router.post("/sales", response_model=SaleResponse, status_code=status.HTTP_201_CREATED)
def create_sale(
    sale_data: SaleCreate,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Create a new sale (cashier only).
    
    Contract:
    - Validates stock availability
    - Snapshots current price
    - Creates ledger entry (-kg)
    - Logs audit trail
    - Atomic transaction
    """
    try:
        # Convert to dict for CRUD
        sale_dict = sale_data.model_dump()
        
        # Create sale via CRUD
        result = crud_ledger.create_sale(
            db,
            sale_data=sale_dict,
            cashier_id=cashier.id
        )
        
        sale = result["sale"]
        
        # Build response
        return SaleResponse(
            id=sale.id,
            sale_number=sale.sale_number,
            item_id=sale.item_id,
            item_name=sale.item.name,
            kg_sold=sale.kg_sold,
            price_per_kg_snapshot=sale.price_per_kg_snapshot,
            total_price=sale.total_price,
            cashier_id=sale.cashier_id,
            cashier_name=sale.cashier.full_name,
            customer_name=sale.customer_name,
            status=sale.status,
            created_at=sale.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sale creation failed: {str(e)}"
        )

@router.get("/sales/me", response_model=SaleListResponse)
def get_my_sales(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Get current cashier's sales.
    Includes both ACTIVE and REVERSED sales for transparency.
    """
    try:
        sales = crud_ledger.get_sales_by_cashier(db, cashier_id=cashier.id, skip=skip, limit=limit)
        
        # Convert to response models
        sale_responses = []
        for sale in sales:
            sale_responses.append(
                SaleResponse(
                    id=sale.id,
                    sale_number=sale.sale_number,
                    item_id=sale.item_id,
                    item_name=sale.item.name,
                    kg_sold=sale.kg_sold,
                    price_per_kg_snapshot=sale.price_per_kg_snapshot,
                    total_price=sale.total_price,
                    cashier_id=sale.cashier_id,
                    cashier_name=sale.cashier.full_name,
                    customer_name=sale.customer_name,
                    status=sale.status,
                    created_at=sale.created_at
                )
            )
        
        return SaleListResponse(
            sales=sale_responses,
            total=len(sale_responses)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve sales: {str(e)}"
        )

@router.post("/sales/{sale_id}/reverse", response_model=SaleReversalResponse)
def reverse_sale(
    sale_id: int,
    reversal_data: SaleReversalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Reverse a sale.
    
    Contract:
    - Only original cashier or admin can reverse
    - Full reversal only (no partial)
    - Reason required
    - Creates reversal record
    - Updates sale status to REVERSED
    - Creates ledger entry (+kg)
    - Logs audit trail
    - Atomic transaction
    """
    try:
        # Get sale to check permissions
        sale = crud_ledger.get_sale_by_id(db, sale_id)
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        # Check permissions: original cashier OR admin
        if current_user.role != "admin" and current_user.id != sale.cashier_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only original cashier or admin can reverse this sale"
            )
        
        # Check if already reversed
        if sale.status == "REVERSED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Sale already reversed"
            )
        
        # Create reversal via CRUD
        reversal_dict = reversal_data.model_dump()
        result = crud_ledger.reverse_sale(
            db,
            sale_id=sale_id,
            reversal_data=reversal_dict,
            user_id=current_user.id
        )
        
        reversal = result["reversal"]
        sale = result["sale"]
        
        # Build response
        return SaleReversalResponse(
            id=reversal.id,
            sale_id=reversal.sale_id,
            sale_number=sale.sale_number,
            reversed_by=reversal.reversed_by,
            reverser_name=current_user.full_name,
            reversal_reason=reversal.reversal_reason,
            created_at=reversal.created_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reversal failed: {str(e)}"
        )

@router.get("/stock")
def get_available_stock(
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Get available stock for all active items.
    Cashier dashboard view.
    """
    try:
        from app.crud.inventory import crud_inventory_item
        from app.schemas.inventory import StockStatusResponse
        from sqlalchemy import select
        
        # Get all active items
        items = crud_inventory_item.get_active_items(db)
        
        stock_list = []
        for item in items:
            stock = crud_ledger.get_item_stock(db, item.id)
            
            # Determine stock status
            if stock <= item.critical_stock_level:
                stock_status = "CRITICAL"
            elif stock <= item.low_stock_level:
                stock_status = "LOW"
            else:
                stock_status = "NORMAL"
            
            stock_value = stock * item.current_price_per_kg
            
            stock_list.append(
                StockStatusResponse(
                    item_id=item.id,
                    name=item.name,
                    total_kg=stock,
                    current_price_per_kg=item.current_price_per_kg,
                    low_stock_level=item.low_stock_level,
                    critical_stock_level=item.critical_stock_level,
                    stock_status=stock_status,
                    stock_value=stock_value
                )
            )
        
        return stock_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stock: {str(e)}"
        )

@router.get("/dashboard")
def get_cashier_dashboard(
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Cashier dashboard.
    Contract: Real-time view of their performance and stock.
    """
    try:
        # Get today's sales for this cashier
        today = date.today()
        stmt_today_sales = select(func.count(Sale.id)).where(
            and_(
                Sale.cashier_id == cashier.id,
                func.date(Sale.created_at) == today
            )
        )
        today_sales_count = db.execute(stmt_today_sales).scalar() or 0
        
        stmt_today_revenue = select(func.coalesce(func.sum(Sale.total_price), 0)).where(
            and_(
                Sale.cashier_id == cashier.id,
                func.date(Sale.created_at) == today,
                Sale.status == "ACTIVE"
            )
        )
        today_revenue = db.execute(stmt_today_revenue).scalar() or Decimal('0')
        
        # Get recent sales
        stmt_recent_sales = (
            select(Sale)
            .where(Sale.cashier_id == cashier.id)
            .order_by(Sale.created_at.desc())
            .limit(10)
            .options(selectinload(Sale.item))
        )
        recent_sales_result = db.execute(stmt_recent_sales)
        recent_sales = recent_sales_result.scalars().all()
        
        # Get stock alerts for items
        from app.utils.alerts import check_stock_alerts
        stock_alerts = check_stock_alerts(db)
        
        # Filter to show only alerts for active items
        active_items_stmt = select(InventoryItem.id).where(InventoryItem.is_active == True)
        active_items_result = db.execute(active_items_stmt)
        active_item_ids = [row[0] for row in active_items_result]
        
        filtered_alerts = [
            alert for alert in stock_alerts 
            if alert.get("item_id") in active_item_ids
        ][:5]  # Limit to 5 most important alerts
        
        return {
            "cashier_name": cashier.full_name,
            "today_sales_count": today_sales_count,
            "today_revenue": float(today_revenue),
            "recent_sales": [
                {
                    "sale_number": sale.sale_number,
                    "item_name": sale.item.name,
                    "kg_sold": float(sale.kg_sold),
                    "total_price": float(sale.total_price),
                    "created_at": sale.created_at,
                    "status": sale.status
                }
                for sale in recent_sales
            ],
            "stock_alerts": filtered_alerts,
            "dashboard_time": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cashier dashboard: {str(e)}"
        )

@router.get("/alerts/stock")
def get_cashier_stock_alerts(
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Get stock alerts relevant to cashier.
    Contract: Transparency in available stock.
    """
    try:
        from app.utils.alerts import check_stock_alerts
        alerts = check_stock_alerts(db)
        
        # Return only critical and low stock alerts
        filtered_alerts = [
            alert for alert in alerts 
            if alert.get("level") in ["CRITICAL", "WARNING"]
        ]
        
        return {
            "alerts": filtered_alerts,
            "total_alerts": len(filtered_alerts),
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve stock alerts: {str(e)}"
        )

@router.get("/sales/{sale_id}/receipt")
def generate_sale_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Generate PDF receipt for a sale.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get sale details
        stmt = (
            select(Sale)
            .join(InventoryItem, Sale.item_id == InventoryItem.id)
            .join(User, Sale.cashier_id == User.id)
            .where(
                and_(
                    Sale.id == sale_id,
                    Sale.cashier_id == cashier.id  # Cashier can only get their own receipts
                )
            )
        )
        
        result = db.execute(stmt)
        sale = result.scalar_one_or_none()
        
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found or access denied"
            )
        
        # Prepare sale data for receipt
        sale_data = {
            "sale_number": sale.sale_number,
            "created_at": sale.created_at.isoformat() if sale.created_at else "",
            "item_name": sale.item.name,
            "kg_sold": float(sale.kg_sold),
            "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
            "total_price": float(sale.total_price) if sale.total_price else 0,
            "cashier_name": sale.cashier.full_name,
            "customer_name": sale.customer_name
        }
        
        # Generate receipt
        pdf_bytes = pdf_generator.generate_receipt(sale_data)
        
        # Return PDF
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=receipt_{sale.sale_number}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library. Please install: pip install reportlab==4.0.4"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate receipt: {str(e)}"
        )

@router.get("/sales/{sale_id}/receipt")
def generate_sale_receipt(
    sale_id: int,
    db: Session = Depends(get_db),
    cashier: User = Depends(get_current_cashier)
):
    """
    Generate PDF receipt for a sale.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get sale details
        stmt = (
            select(Sale)
            .join(InventoryItem, Sale.item_id == InventoryItem.id)
            .join(User, Sale.cashier_id == User.id)
            .where(
                and_(
                    Sale.id == sale_id,
                    Sale.cashier_id == cashier.id  # Cashier can only get their own receipts
                )
            )
        )
        
        result = db.execute(stmt)
        sale = result.scalar_one_or_none()
        
        if not sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found or access denied"
            )
        
        # Prepare sale data for receipt
        sale_data = {
            "sale_number": sale.sale_number,
            "created_at": sale.created_at.isoformat() if sale.created_at else "",
            "item_name": sale.item.name,
            "kg_sold": float(sale.kg_sold),
            "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
            "total_price": float(sale.total_price) if sale.total_price else 0,
            "cashier_name": sale.cashier.full_name,
            "customer_name": sale.customer_name
        }
        
        # Generate receipt
        pdf_bytes = pdf_generator.generate_receipt(sale_data)
        
        # Return PDF
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=receipt_{sale.sale_number}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library. Please install: pip install reportlab==4.0.4"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate receipt: {str(e)}"
        )
