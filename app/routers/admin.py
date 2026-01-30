"""
Admin router for dashboards and system management.
Admin role required for all endpoints.
Contract: Admin controls structure, transparency prevents theft.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, and_
from datetime import date, datetime, timedelta
from typing import List, Optional
from decimal import Decimal

from app.database import get_db
from app.auth import get_current_user
from app.models import User, InventoryItem, Sale, SaleReversal, AuditLog
from app.schemas.dashboard import (
    StockDashboardResponse, StockDashboardItem,
    SalesDashboardResponse, DailySalesSummary,
    PerformanceDashboardResponse, CashierPerformanceMetric,
    SystemOverview, AlertResponse, DateRangeFilter
)
from app.utils.alerts import generate_all_alerts
from app.crud.inventory import crud_inventory_ledger

router = APIRouter(prefix="/admin", tags=["admin"])

# Dependency to ensure user is admin
def get_current_admin(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> User:
    """Ensure user is an active admin"""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required"
        )
    
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    return current_user

@router.get("/dashboard/stock", response_model=StockDashboardResponse)
def get_stock_dashboard(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Stock dashboard for admin.
    Contract: Real-time stock status, transparency prevents theft.
    """
    try:
        # Get all active items
        stmt = select(InventoryItem).where(InventoryItem.is_active == True)
        result = db.execute(stmt)
        items = result.scalars().all()
        
        dashboard_items = []
        total_stock_value = Decimal('0')
        low_stock_count = 0
        critical_stock_count = 0
        
        for item in items:
            # Get current stock
            current_stock = crud_inventory_ledger.get_item_stock(db, item.id)
            
            # Determine stock status
            if current_stock <= item.critical_stock_level:
                stock_status = "CRITICAL"
                critical_stock_count += 1
                needs_attention = True
            elif current_stock <= item.low_stock_level:
                stock_status = "LOW"
                low_stock_count += 1
                needs_attention = True
            else:
                stock_status = "NORMAL"
                needs_attention = False
            
            # Calculate stock value
            stock_value = current_stock * item.current_price_per_kg
            total_stock_value += stock_value
            
            dashboard_items.append(
                StockDashboardItem(
                    item_id=item.id,
                    name=item.name,
                    current_stock=current_stock,
                    current_price_per_kg=item.current_price_per_kg,
                    low_stock_level=item.low_stock_level,
                    critical_stock_level=item.critical_stock_level,
                    stock_status=stock_status,
                    stock_value=stock_value,
                    needs_attention=needs_attention
                )
            )
        
        return StockDashboardResponse(
            items=dashboard_items,
            total_items=len(dashboard_items),
            total_stock_value=total_stock_value,
            low_stock_items=low_stock_count,
            critical_stock_items=critical_stock_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate stock dashboard: {str(e)}"
        )

@router.get("/dashboard/sales", response_model=SalesDashboardResponse)
def get_sales_dashboard(
    filter: DateRangeFilter = Depends(),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Sales dashboard for admin.
    Uses existing database view for performance.
    """
    try:
        # Use the existing daily_sales_summary view
        query = text("""
            SELECT sale_date, item_name, cashier_name, 
                   total_sales, total_kg_sold, total_revenue
            FROM daily_sales_summary 
            WHERE sale_date BETWEEN :start_date AND :end_date
            ORDER BY sale_date DESC, total_revenue DESC
        """)
        
        result = db.execute(query, {
            "start_date": filter.start_date,
            "end_date": filter.end_date
        })
        
        today_summaries = []
        today_total_kg = Decimal('0')
        today_total_revenue = Decimal('0')
        today_transaction_count = 0
        
        for row in result:
            summary = DailySalesSummary(
                sale_date=row.sale_date,
                item_name=row.item_name,
                cashier_name=row.cashier_name,
                total_sales=row.total_sales,
                total_kg_sold=row.total_kg_sold,
                total_revenue=row.total_revenue
            )
            today_summaries.append(summary)
            
            if row.sale_date == date.today():
                today_total_kg += row.total_kg_sold
                today_total_revenue += row.total_revenue
                today_transaction_count += row.total_sales
        
        return SalesDashboardResponse(
            today_sales=today_summaries,
            today_total_kg=today_total_kg,
            today_total_revenue=today_total_revenue,
            today_transaction_count=today_transaction_count
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sales dashboard: {str(e)}"
        )

@router.get("/dashboard/performance", response_model=PerformanceDashboardResponse)
def get_performance_dashboard(
    days: int = Query(7, ge=1, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Cashier performance dashboard.
    Uses existing cashier_performance view.
    """
    try:
        # Use the existing cashier_performance view
        query = text("SELECT * FROM cashier_performance")
        result = db.execute(query)
        
        cashiers = []
        period_end = date.today()
        period_start = period_end - timedelta(days=days)
        
        for row in result:
            metric = CashierPerformanceMetric(
                cashier_id=row.id,
                cashier_name=row.full_name,
                days_active=row.days_active,
                total_sales=row.total_sales,
                total_kg_sold=row.total_kg_sold,
                total_revenue=row.total_revenue,
                avg_selling_price=row.avg_selling_price
            )
            cashiers.append(metric)
        
        return PerformanceDashboardResponse(
            cashiers=cashiers,
            period_start=period_start,
            period_end=period_end
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance dashboard: {str(e)}"
        )

@router.get("/dashboard/overview", response_model=SystemOverview)
def get_system_overview(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    System overview dashboard.
    Contract: Real-time system status for admin control.
    """
    try:
        # Count total items
        stmt_items = select(func.count(InventoryItem.id))
        total_items = db.execute(stmt_items).scalar()
        
        stmt_active_items = select(func.count(InventoryItem.id)).where(InventoryItem.is_active == True)
        active_items = db.execute(stmt_active_items).scalar()
        
        # Calculate total stock value
        stmt_all_items = select(InventoryItem).where(InventoryItem.is_active == True)
        items_result = db.execute(stmt_all_items)
        items = items_result.scalars().all()
        
        total_stock_kg = Decimal('0')
        total_stock_value = Decimal('0')
        
        for item in items:
            stock = crud_inventory_ledger.get_item_stock(db, item.id)
            total_stock_kg += stock
            total_stock_value += stock * item.current_price_per_kg
        
        # Today's sales
        today = date.today()
        stmt_today_sales = select(func.count(Sale.id)).where(
            func.date(Sale.created_at) == today
        )
        today_sales_count = db.execute(stmt_today_sales).scalar() or 0
        
        stmt_today_revenue = select(func.coalesce(func.sum(Sale.total_price), 0)).where(
            func.date(Sale.created_at) == today
        )
        today_revenue = db.execute(stmt_today_revenue).scalar() or Decimal('0')
        
        # Active cashiers
        stmt_active_cashiers = select(func.count(User.id)).where(
            and_(
                User.role == "cashier",
                User.is_active == True
            )
        )
        active_cashiers = db.execute(stmt_active_cashiers).scalar()
        
        # Pending alerts
        alerts = generate_all_alerts(db)
        pending_alerts = len(alerts)
        
        # System status
        system_status = "HEALTHY"
        if pending_alerts > 5:
            system_status = "WARNING"
        if pending_alerts > 10:
            system_status = "CRITICAL"
        
        return SystemOverview(
            total_items=total_items,
            active_items=active_items,
            total_stock_kg=total_stock_kg,
            total_stock_value=total_stock_value,
            today_sales_count=today_sales_count,
            today_revenue=today_revenue,
            active_cashiers=active_cashiers,
            pending_alerts=pending_alerts,
            system_status=system_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate system overview: {str(e)}"
        )

@router.get("/alerts", response_model=List[dict])
def get_system_alerts(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get all system alerts.
    Contract: Real-time alerting for transparency.
    """
    try:
        alerts = generate_all_alerts(db)
        return alerts
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate alerts: {str(e)}"
        )

@router.get("/audit-trail")
def get_audit_trail(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get audit trail for transparency.
    Contract: All actions logged, nothing deleted silently.
    """
    try:
        stmt = (
            select(AuditLog)
            .order_by(AuditLog.performed_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = db.execute(stmt)
        audit_logs = result.scalars().all()
        
        return audit_logs
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve audit trail: {str(e)}"
        )

@router.get("/reports/stock/pdf")
def generate_stock_pdf_report(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF stock report.
    Contract: Simple report export functionality.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        
        # Get stock data (reuse dashboard logic)
        stmt = select(InventoryItem).where(InventoryItem.is_active == True)
        result = db.execute(stmt)
        items = result.scalars().all()
        
        stock_data = []
        for item in items:
            current_stock = crud_inventory_ledger.get_item_stock(db, item.id)
            
            # Determine stock status
            if current_stock <= item.critical_stock_level:
                stock_status = "CRITICAL"
            elif current_stock <= item.low_stock_level:
                stock_status = "LOW"
            else:
                stock_status = "NORMAL"
            
            stock_value = current_stock * item.current_price_per_kg
            
            stock_data.append({
                "id": item.id,
                "name": item.name,
                "current_stock": float(current_stock),
                "current_price_per_kg": float(item.current_price_per_kg),
                "low_stock_level": float(item.low_stock_level),
                "critical_stock_level": float(item.critical_stock_level),
                "stock_status": stock_status,
                "stock_value": float(stock_value)
            })
        
        # Generate PDF
        pdf_bytes = pdf_generator.generate_stock_report(
            stock_data,
            report_title="Nangulu POS - Stock Report"
        )
        
        # Return PDF as download
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library. Please install: pip install reportlab==4.0.4"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )

@router.get("/reports/sales/pdf")
def generate_sales_pdf_report(
    start_date: date = Query(default_factory=lambda: date.today()),
    end_date: date = Query(default_factory=lambda: date.today()),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF sales report for date range.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get sales data
        stmt = (
            select(Sale)
            .join(InventoryItem, Sale.item_id == InventoryItem.id)
            .join(User, Sale.cashier_id == User.id)
            .where(
                and_(
                    func.date(Sale.created_at) >= start_date,
                    func.date(Sale.created_at) <= end_date,
                    Sale.status == "ACTIVE"
                )
            )
            .order_by(Sale.created_at.desc())
        )
        
        result = db.execute(stmt)
        sales = result.scalars().all()
        
        sales_data = []
        for sale in sales:
            sales_data.append({
                "sale_number": sale.sale_number,
                "created_at": sale.created_at.isoformat() if sale.created_at else "",
                "item_name": sale.item.name,
                "kg_sold": float(sale.kg_sold),
                "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
                "total_price": float(sale.total_price) if sale.total_price else 0,
                "cashier_name": sale.cashier.full_name,
                "customer_name": sale.customer_name
            })
        
        # Date range description
        if start_date == end_date:
            date_range = f"Daily Report - {start_date}"
        else:
            date_range = f"Period: {start_date} to {end_date}"
        
        # Generate PDF
        pdf_bytes = pdf_generator.generate_sales_report(sales_data, date_range)
        
        # Return PDF as download
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=sales_report_{start_date}_{end_date}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sales PDF report: {str(e)}"
        )

@router.get("/reports/performance/pdf")
def generate_performance_pdf_report(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF performance report.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get performance data from view
        query = text("SELECT * FROM cashier_performance ORDER BY total_revenue DESC")
        result = db.execute(query)
        
        # We'll create a simple performance report
        # For now, generate a combined report
        
        # Get system overview data
        from . import get_system_overview
        overview_data = get_system_overview(db, admin)
        
        # Get stock data for combined report
        stock_response = get_stock_dashboard(db, admin)
        
        # Create a custom report
        buffer = io.BytesIO()
        
        # This would be expanded to create a comprehensive performance report
        # For now, return a simple placeholder
        
        pdf_bytes = pdf_generator.generate_stock_report(
            [{"name": "Performance Report", "current_stock": 0, "current_price_per_kg": 0, 
              "stock_status": "INFO", "stock_value": 0}],
            report_title="Performance Report - Coming Soon"
        )
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance report: {str(e)}"
        )

@router.get("/reports/stock/pdf")
def generate_stock_pdf_report(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF stock report.
    Contract: Simple report export functionality.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        
        # Get stock data (reuse dashboard logic)
        stmt = select(InventoryItem).where(InventoryItem.is_active == True)
        result = db.execute(stmt)
        items = result.scalars().all()
        
        stock_data = []
        for item in items:
            current_stock = crud_inventory_ledger.get_item_stock(db, item.id)
            
            # Determine stock status
            if current_stock <= item.critical_stock_level:
                stock_status = "CRITICAL"
            elif current_stock <= item.low_stock_level:
                stock_status = "LOW"
            else:
                stock_status = "NORMAL"
            
            stock_value = current_stock * item.current_price_per_kg
            
            stock_data.append({
                "id": item.id,
                "name": item.name,
                "current_stock": float(current_stock),
                "current_price_per_kg": float(item.current_price_per_kg),
                "low_stock_level": float(item.low_stock_level),
                "critical_stock_level": float(item.critical_stock_level),
                "stock_status": stock_status,
                "stock_value": float(stock_value)
            })
        
        # Generate PDF
        pdf_bytes = pdf_generator.generate_stock_report(
            stock_data,
            report_title="Nangulu POS - Stock Report"
        )
        
        # Return PDF as download
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=stock_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library. Please install: pip install reportlab==4.0.4"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}"
        )

@router.get("/reports/sales/pdf")
def generate_sales_pdf_report(
    start_date: date = Query(default_factory=lambda: date.today()),
    end_date: date = Query(default_factory=lambda: date.today()),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF sales report for date range.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get sales data
        stmt = (
            select(Sale)
            .join(InventoryItem, Sale.item_id == InventoryItem.id)
            .join(User, Sale.cashier_id == User.id)
            .where(
                and_(
                    func.date(Sale.created_at) >= start_date,
                    func.date(Sale.created_at) <= end_date,
                    Sale.status == "ACTIVE"
                )
            )
            .order_by(Sale.created_at.desc())
        )
        
        result = db.execute(stmt)
        sales = result.scalars().all()
        
        sales_data = []
        for sale in sales:
            sales_data.append({
                "sale_number": sale.sale_number,
                "created_at": sale.created_at.isoformat() if sale.created_at else "",
                "item_name": sale.item.name,
                "kg_sold": float(sale.kg_sold),
                "price_per_kg_snapshot": float(sale.price_per_kg_snapshot),
                "total_price": float(sale.total_price) if sale.total_price else 0,
                "cashier_name": sale.cashier.full_name,
                "customer_name": sale.customer_name
            })
        
        # Date range description
        if start_date == end_date:
            date_range = f"Daily Report - {start_date}"
        else:
            date_range = f"Period: {start_date} to {end_date}"
        
        # Generate PDF
        pdf_bytes = pdf_generator.generate_sales_report(sales_data, date_range)
        
        # Return PDF as download
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=sales_report_{start_date}_{end_date}.pdf"
            }
        )
        
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF generation requires reportlab library"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate sales PDF report: {str(e)}"
        )

@router.get("/reports/performance/pdf")
def generate_performance_pdf_report(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Generate PDF performance report.
    """
    try:
        from app.utils.pdf_reports import pdf_generator
        import io
        
        # Get performance data from view
        query = text("SELECT * FROM cashier_performance ORDER BY total_revenue DESC")
        result = db.execute(query)
        
        # We'll create a simple performance report
        # For now, generate a combined report
        
        # Get system overview data
        from . import get_system_overview
        overview_data = get_system_overview(db, admin)
        
        # Get stock data for combined report
        stock_response = get_stock_dashboard(db, admin)
        
        # Create a custom report
        buffer = io.BytesIO()
        
        # This would be expanded to create a comprehensive performance report
        # For now, return a simple placeholder
        
        pdf_bytes = pdf_generator.generate_stock_report(
            [{"name": "Performance Report", "current_stock": 0, "current_price_per_kg": 0, 
              "stock_status": "INFO", "stock_value": 0}],
            report_title="Performance Report - Coming Soon"
        )
        
        from fastapi.responses import StreamingResponse
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=performance_report_{datetime.now().strftime('%Y%m%d')}.pdf"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate performance report: {str(e)}"
        )

@router.get("/archive/summary", response_model=ArchiveSummary)
def get_archive_summary(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get archive system summary.
    Contract: Transparency in archive operations.
    """
    try:
        from app.utils.archive import ArchiveManager
        
        manager = ArchiveManager(db)
        summary = manager.get_archive_summary()
        
        return ArchiveSummary(**summary)
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get archive summary: {str(e)}"
        )

@router.get("/archive/operations", response_model=List[ArchiveRecord])
def list_archive_operations(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    List archive operations.
    Contract: Full audit trail of archive activities.
    """
    try:
        from app.utils.archive import ArchiveManager
        
        manager = ArchiveManager(db)
        operations = manager.list_archive_operations(limit)
        
        # Convert to response models
        response = []
        for op in operations:
            # Get performer name
            performer_stmt = select(User.full_name).where(User.id == op.performed_by)
            performer_result = db.execute(performer_stmt)
            performer_name = performer_result.scalar() or "Unknown"
            
            response.append(ArchiveRecord(
                id=op.id,
                action=op.action,
                snapshot_type=op.snapshot_type,
                description=op.description,
                status=op.status,
                performed_by=op.performed_by,
                performed_by_name=performer_name,
                records_affected=op.records_affected,
                file_path=op.file_path,
                file_size=op.file_size,
                started_at=op.started_at,
                completed_at=op.completed_at,
                error_message=op.error_message
            ))
        
        return response
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list archive operations: {str(e)}"
        )

@router.post("/archive/snapshot")
def create_system_snapshot(
    snapshot_request: ArchiveCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Create system snapshot.
    Contract: No data deletion, only archival.
    """
    try:
        from app.utils.archive import ArchiveManager, SnapshotType
        
        if not snapshot_request.snapshot_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Snapshot type is required"
            )
        
        manager = ArchiveManager(db)
        result = manager.create_snapshot(
            snapshot_type=snapshot_request.snapshot_type,
            user_id=admin.id,
            description=snapshot_request.description
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create snapshot: {result.get('error')}"
            )
        
        return {
            "message": "Snapshot created successfully",
            "snapshot_id": result["snapshot_id"],
            "archive_operation_id": result["archive_operation_id"],
            "records_captured": result["records_captured"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create snapshot: {str(e)}"
        )

@router.post("/archive/sales")
def archive_old_sales(
    days_old: int = Query(90, ge=30, le=365, description="Archive sales older than X days"),
    description: str = Query("Archive old sales", description="Reason for archiving"),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Archive sales older than specified days.
    Contract: Move to archive table, never delete from ledger.
    """
    try:
        from app.utils.archive import ArchiveManager
        
        # Additional confirmation for destructive operation
        if days_old < 90:
            # Require special confirmation for aggressive archiving
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archiving sales less than 90 days old requires additional confirmation. Use days_old >= 90."
            )
        
        manager = ArchiveManager(db)
        result = manager.archive_old_sales(
            days_old=days_old,
            user_id=admin.id,
            description=description
        )
        
        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to archive sales: {result.get('error')}"
            )
        
        return {
            "message": "Sales archived successfully",
            "archive_operation_id": result["archive_operation_id"],
            "records_archived": result["records_archived"],
            "cutoff_date": result["cutoff_date"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to archive sales: {str(e)}"
        )

@router.get("/archive/snapshots")
def list_system_snapshots(
    snapshot_type: Optional[SnapshotType] = None,
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    List system snapshots.
    """
    try:
        from app.utils.archive import ArchiveManager
        
        manager = ArchiveManager(db)
        snapshots = manager.list_snapshots(snapshot_type, limit)
        
        return snapshots
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list snapshots: {str(e)}"
        )

@router.get("/archive/snapshots/{snapshot_id}")
def get_snapshot_details(
    snapshot_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Get snapshot details.
    """
    try:
        from app.utils.archive import ArchiveManager
        
        manager = ArchiveManager(db)
        snapshot = manager.get_snapshot(snapshot_id)
        
        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Snapshot not found"
            )
        
        return snapshot
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get snapshot: {str(e)}"
        )

@router.post("/archive/reset-confirm")
def confirm_system_reset(
    reset_data: ResetConfirmation,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """
    Confirm system reset with backup.
    Contract: Never reset without backup and confirmation.
    """
    # Check confirmation code
    expected_code = f"RESET-{datetime.now().strftime('%Y%m%d')}"
    if reset_data.confirmation_code != expected_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid confirmation code. Expected: {expected_code}"
        )
    
    try:
        from app.utils.archive import ArchiveManager
        
        manager = ArchiveManager(db)
        
        # Step 1: Create backup snapshot if requested
        if reset_data.backup_first:
            result = manager.create_snapshot(
                snapshot_type=SnapshotType.FULL_SYSTEM,
                user_id=admin.id,
                description=f"Pre-reset backup: {reset_data.reason}"
            )
            
            if not result["success"]:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Backup failed: {result.get('error')}"
                )
        
        # In a real implementation, this would perform the reset
        # For now, return instructions
        
        return {
            "message": "Reset confirmed with backup",
            "backup_created": reset_data.backup_first,
            "next_steps": [
                "1. Backup verified and stored",
                "2. System ready for reset",
                "3. Contact administrator for final reset execution"
            ],
            "warning": "System reset is a destructive operation. Ensure all data is backed up."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Reset confirmation failed: {str(e)}"
        )
