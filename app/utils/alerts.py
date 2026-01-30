"""
Alert generation utility.
Contract: Real-time stock monitoring, prevent theft via transparency.
"""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from app.models import InventoryItem, AuditLog, Sale
from app.schemas.dashboard import AlertType, AlertLevel

def check_stock_alerts(db: Session) -> List[dict]:
    """
    Check for stock level alerts.
    Uses existing current_stock view via SQLAlchemy.
    """
    alerts = []
    
    try:
        # Contract: Use operational DB patterns, not analytical
        # Check all active items for stock levels
        stmt = select(InventoryItem).where(InventoryItem.is_active == True)
        result = db.execute(stmt)
        items = result.scalars().all()
        
        for item in items:
            # Get current stock using existing ledger calculation
            from app.crud.inventory import crud_inventory_ledger
            current_stock = crud_inventory_ledger.get_item_stock(db, item.id)
            
            # Check critical stock
            if current_stock <= item.critical_stock_level:
                alerts.append({
                    "alert_type": AlertType.STOCK_CRITICAL,
                    "level": AlertLevel.CRITICAL,
                    "message": f"{item.name} stock is CRITICAL: {current_stock} kg (threshold: {item.critical_stock_level} kg)",
                    "item_id": item.id
                })
            # Check low stock
            elif current_stock <= item.low_stock_level:
                alerts.append({
                    "alert_type": AlertType.STOCK_LOW,
                    "level": AlertLevel.WARNING,
                    "message": f"{item.name} stock is LOW: {current_stock} kg (threshold: {item.low_stock_level} kg)",
                    "item_id": item.id
                })
        
        return alerts
        
    except Exception as e:
        # Log error but don't crash
        print(f"Error checking stock alerts: {e}")
        return []

def check_system_alerts(db: Session) -> List[dict]:
    """
    Check for system-level alerts.
    Contract: Monitor unusual activities.
    """
    alerts = []
    
    try:
        # Check for failed login attempts (last hour)
        hour_ago = datetime.utcnow() - timedelta(hours=1)
        
        # This would check audit logs for failed logins
        # For now, return empty - will be implemented with audit log monitoring
        
        # Check for database connection issues
        # (Already covered by health endpoint)
        
        return alerts
        
    except Exception as e:
        print(f"Error checking system alerts: {e}")
        return []

def check_performance_alerts(db: Session) -> List[dict]:
    """
    Check for performance-related alerts.
    Contract: Transparency in operations.
    """
    alerts = []
    
    try:
        # Check for unusually high sales (potential errors)
        today = datetime.utcnow().date()
        
        stmt = select(Sale).where(
            Sale.created_at >= datetime.combine(today, datetime.min.time())
        )
        result = db.execute(stmt)
        today_sales = result.scalars().all()
        
        if len(today_sales) > 100:  # Arbitrary threshold
            alerts.append({
                "alert_type": AlertType.PERFORMANCE,
                "level": AlertLevel.INFO,
                "message": f"High sales volume today: {len(today_sales)} transactions",
                "item_id": None
            })
        
        return alerts
        
    except Exception as e:
        print(f"Error checking performance alerts: {e}")
        return []

def generate_all_alerts(db: Session) -> List[dict]:
    """
    Generate all system alerts.
    Contract: Real-time monitoring for transparency.
    """
    all_alerts = []
    
    # Stock alerts
    stock_alerts = check_stock_alerts(db)
    all_alerts.extend(stock_alerts)
    
    # System alerts
    system_alerts = check_system_alerts(db)
    all_alerts.extend(system_alerts)
    
    # Performance alerts
    perf_alerts = check_performance_alerts(db)
    all_alerts.extend(perf_alerts)
    
    return all_alerts
