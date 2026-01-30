"""
Archive and snapshot utilities.
Contract: No silent deletes, maintain full audit trail.
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, select, func, and_, or_

from app.models import (
    ArchiveOperation, SystemSnapshot, ArchivedSale,
    Sale, InventoryItem, InventoryLedger, User
)
from app.schemas.archive import ArchiveAction, SnapshotType, ArchiveStatus

class ArchiveManager:
    """Manage archive and snapshot operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_snapshot(self, snapshot_type: SnapshotType, user_id: int, 
                       description: str = "System snapshot") -> Dict:
        """
        Create system snapshot.
        Contract: No data deletion, only archival.
        """
        try:
            # Start transaction
            self.db.begin()
            
            # Create archive operation record
            archive_op = ArchiveOperation(
                action=ArchiveAction.SNAPSHOT.value,
                snapshot_type=snapshot_type.value,
                description=description,
                performed_by=user_id,
                status=ArchiveStatus.PENDING.value,
                started_at=datetime.utcnow()
            )
            self.db.add(archive_op)
            self.db.flush()  # Get ID
            
            # Collect snapshot data
            snapshot_data = self._collect_snapshot_data(snapshot_type)
            
            # Store snapshot
            snapshot = SystemSnapshot(
                snapshot_type=snapshot_type.value,
                snapshot_data=snapshot_data,
                created_by=user_id,
                expires_at=datetime.utcnow() + timedelta(days=90),
                is_active=True
            )
            self.db.add(snapshot)
            
            # Update archive operation
            archive_op.status = ArchiveStatus.COMPLETED.value
            archive_op.completed_at = datetime.utcnow()
            archive_op.records_affected = self._count_records_in_snapshot(snapshot_data)
            
            self.db.commit()
            
            return {
                "success": True,
                "snapshot_id": snapshot.id,
                "archive_operation_id": archive_op.id,
                "records_captured": archive_op.records_affected
            }
            
        except Exception as e:
            self.db.rollback()
            
            # Log failed operation
            if 'archive_op' in locals():
                archive_op.status = ArchiveStatus.FAILED.value
                archive_op.completed_at = datetime.utcnow()
                archive_op.error_message = str(e)
                self.db.commit()
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def _collect_snapshot_data(self, snapshot_type: SnapshotType) -> Dict:
        """Collect data for snapshot based on type."""
        data = {
            "timestamp": datetime.utcnow().isoformat(),
            "snapshot_type": snapshot_type.value
        }
        
        if snapshot_type == SnapshotType.FULL_SYSTEM:
            data["inventory"] = self._get_inventory_summary()
            data["sales"] = self._get_sales_summary(days=7)
            data["users"] = self._get_users_summary()
            data["system_health"] = self._get_system_health()
            
        elif snapshot_type == SnapshotType.SALES_ONLY:
            data["sales_summary"] = self._get_sales_summary(days=30)
            data["recent_sales"] = self._get_recent_sales(limit=1000)
            
        elif snapshot_type == SnapshotType.INVENTORY_ONLY:
            data["inventory"] = self._get_inventory_summary()
            data["ledger_summary"] = self._get_ledger_summary()
            
        return data
    
    def _get_inventory_summary(self) -> List[Dict]:
        """Get inventory summary for snapshot."""
        stmt = select(InventoryItem).where(InventoryItem.is_active == True)
        result = self.db.execute(stmt)
        items = result.scalars().all()
        
        summary = []
        for item in items:
            # Get current stock
            stock_stmt = select(func.coalesce(func.sum(InventoryLedger.kg_change), 0)).where(
                InventoryLedger.item_id == item.id
            )
            stock_result = self.db.execute(stock_stmt)
            current_stock = stock_result.scalar() or 0
            
            summary.append({
                "id": item.id,
                "name": item.name,
                "current_price_per_kg": float(item.current_price_per_kg),
                "current_stock": float(current_stock),
                "stock_value": float(current_stock * item.current_price_per_kg),
                "low_stock_level": float(item.low_stock_level),
                "critical_stock_level": float(item.critical_stock_level),
                "is_active": item.is_active
            })
        
        return summary
    
    def _get_sales_summary(self, days: int = 7) -> Dict:
        """Get sales summary for given period."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Count sales
        count_stmt = select(func.count(Sale.id)).where(
            and_(
                Sale.created_at >= cutoff_date,
                Sale.status == "ACTIVE"
            )
        )
        count_result = self.db.execute(count_stmt)
        sales_count = count_result.scalar() or 0
        
        # Total revenue
        revenue_stmt = select(func.coalesce(func.sum(Sale.total_price), 0)).where(
            and_(
                Sale.created_at >= cutoff_date,
                Sale.status == "ACTIVE"
            )
        )
        revenue_result = self.db.execute(revenue_stmt)
        total_revenue = revenue_result.scalar() or 0
        
        # Top items
        top_items_stmt = text("""
            SELECT i.name, COUNT(s.id) as sales_count, 
                   SUM(s.kg_sold) as total_kg, SUM(s.total_price) as total_revenue
            FROM sales s
            JOIN inventory_items i ON s.item_id = i.id
            WHERE s.created_at >= :cutoff AND s.status = 'ACTIVE'
            GROUP BY i.id, i.name
            ORDER BY total_revenue DESC
            LIMIT 5
        """)
        top_items_result = self.db.execute(top_items_stmt, {"cutoff": cutoff_date})
        top_items = [
            {
                "name": row[0],
                "sales_count": row[1],
                "total_kg": float(row[2]),
                "total_revenue": float(row[3])
            }
            for row in top_items_result
        ]
        
        return {
            "period_days": days,
            "sales_count": sales_count,
            "total_revenue": float(total_revenue),
            "avg_daily_sales": sales_count / days if days > 0 else 0,
            "top_items": top_items,
            "cutoff_date": cutoff_date.isoformat()
        }
    
    def _get_recent_sales(self, limit: int = 100) -> List[Dict]:
        """Get recent sales for snapshot."""
        stmt = (
            select(Sale)
            .where(Sale.status == "ACTIVE")
            .order_by(Sale.created_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt)
        sales = result.scalars().all()
        
        return [
            {
                "id": sale.id,
                "sale_number": sale.sale_number,
                "item_id": sale.item_id,
                "kg_sold": float(sale.kg_sold),
                "total_price": float(sale.total_price) if sale.total_price else 0,
                "cashier_id": sale.cashier_id,
                "created_at": sale.created_at.isoformat() if sale.created_at else None
            }
            for sale in sales
        ]
    
    def _get_users_summary(self) -> Dict:
        """Get users summary."""
        stmt = select(User)
        result = self.db.execute(stmt)
        users = result.scalars().all()
        
        active_admins = sum(1 for u in users if u.role == "admin" and u.is_active)
        active_cashiers = sum(1 for u in users if u.role == "cashier" and u.is_active)
        
        return {
            "total_users": len(users),
            "active_admins": active_admins,
            "active_cashiers": active_cashiers,
            "inactive_users": len(users) - (active_admins + active_cashiers)
        }
    
    def _get_system_health(self) -> Dict:
        """Get system health metrics."""
        # Check database connectivity
        db_health = "HEALTHY"
        try:
            self.db.execute(text("SELECT 1"))
        except:
            db_health = "UNHEALTHY"
        
        # Count pending operations
        pending_stmt = select(func.count(ArchiveOperation.id)).where(
            ArchiveOperation.status == "PENDING"
        )
        pending_result = self.db.execute(pending_stmt)
        pending_ops = pending_result.scalar() or 0
        
        return {
            "database": db_health,
            "pending_archive_operations": pending_ops,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def _get_ledger_summary(self) -> Dict:
        """Get ledger summary."""
        # Total ledger entries
        total_stmt = select(func.count(InventoryLedger.id))
        total_result = self.db.execute(total_stmt)
        total_entries = total_result.scalar() or 0
        
        # Last 30 days activity
        month_ago = datetime.utcnow() - timedelta(days=30)
        recent_stmt = select(func.count(InventoryLedger.id)).where(
            InventoryLedger.created_at >= month_ago
        )
        recent_result = self.db.execute(recent_stmt)
        recent_entries = recent_result.scalar() or 0
        
        return {
            "total_entries": total_entries,
            "recent_entries_30d": recent_entries,
            "avg_daily_entries": recent_entries / 30 if recent_entries > 0 else 0
        }
    
    def _count_records_in_snapshot(self, snapshot_data: Dict) -> int:
        """Count records in snapshot data."""
        count = 0
        if "inventory" in snapshot_data:
            count += len(snapshot_data["inventory"])
        if "recent_sales" in snapshot_data:
            count += len(snapshot_data["recent_sales"])
        if "sales_summary" in snapshot_data and "top_items" in snapshot_data["sales_summary"]:
            count += len(snapshot_data["sales_summary"]["top_items"])
        return count
    
    def archive_old_sales(self, days_old: int, user_id: int, 
                         description: str = "Archive old sales") -> Dict:
        """
        Archive sales older than specified days.
        Contract: Move to archive table, never delete.
        """
        try:
            self.db.begin()
            
            # Create archive operation record
            archive_op = ArchiveOperation(
                action=ArchiveAction.RESET.value,
                description=description,
                performed_by=user_id,
                status=ArchiveStatus.PENDING.value,
                started_at=datetime.utcnow()
            )
            self.db.add(archive_op)
            self.db.flush()
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days_old)
            
            # Find sales to archive
            sales_stmt = select(Sale).where(
                and_(
                    Sale.created_at < cutoff_date,
                    Sale.status == "ACTIVE"
                )
            )
            sales_result = self.db.execute(sales_stmt)
            sales_to_archive = sales_result.scalars().all()
            
            records_archived = 0
            
            # Archive each sale
            for sale in sales_to_archive:
                archived_sale = ArchivedSale(
                    id=sale.id,
                    sale_number=sale.sale_number,
                    item_id=sale.item_id,
                    kg_sold=sale.kg_sold,
                    price_per_kg_snapshot=sale.price_per_kg_snapshot,
                    total_price=sale.total_price,
                    cashier_id=sale.cashier_id,
                    customer_name=sale.customer_name,
                    status=sale.status,
                    original_created_at=sale.created_at,
                    archive_operation_id=archive_op.id
                )
                self.db.add(archived_sale)
                records_archived += 1
            
            # Delete from main table (now archived)
            if records_archived > 0:
                delete_stmt = text("""
                    DELETE FROM sales 
                    WHERE id IN (
                        SELECT id FROM archived_sales 
                        WHERE archive_operation_id = :op_id
                    )
                """)
                self.db.execute(delete_stmt, {"op_id": archive_op.id})
            
            # Update archive operation
            archive_op.status = ArchiveStatus.COMPLETED.value
            archive_op.completed_at = datetime.utcnow()
            archive_op.records_affected = records_archived
            
            self.db.commit()
            
            return {
                "success": True,
                "archive_operation_id": archive_op.id,
                "records_archived": records_archived,
                "cutoff_date": cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.db.rollback()
            
            if 'archive_op' in locals():
                archive_op.status = ArchiveStatus.FAILED.value
                archive_op.completed_at = datetime.utcnow()
                archive_op.error_message = str(e)
                self.db.commit()
            
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_archive_summary(self) -> Dict:
        """Get archive system summary."""
        # Use the database view
        summary_stmt = text("SELECT * FROM archive_summary_view")
        result = self.db.execute(summary_stmt)
        row = result.first()
        
        if row:
            return {
                "total_archives": row[0],
                "pending_operations": row[1],
                "last_snapshot": row[2].isoformat() if row[2] else None,
                "total_storage_used": row[3],
                "oldest_record_date": row[4].isoformat() if row[4] else None
            }
        
        return {
            "total_archives": 0,
            "pending_operations": 0,
            "last_snapshot": None,
            "total_storage_used": 0,
            "oldest_record_date": None
        }
    
    def list_archive_operations(self, limit: int = 50) -> List[ArchiveOperation]:
        """List recent archive operations."""
        stmt = (
            select(ArchiveOperation)
            .order_by(ArchiveOperation.started_at.desc())
            .limit(limit)
        )
        result = self.db.execute(stmt)
        return result.scalars().all()
    
    def get_snapshot(self, snapshot_id: int) -> Optional[SystemSnapshot]:
        """Get snapshot by ID."""
        stmt = select(SystemSnapshot).where(SystemSnapshot.id == snapshot_id)
        result = self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    def list_snapshots(self, snapshot_type: Optional[SnapshotType] = None, 
                      limit: int = 20) -> List[SystemSnapshot]:
        """List system snapshots."""
        stmt = select(SystemSnapshot).where(SystemSnapshot.is_active == True)
        
        if snapshot_type:
            stmt = stmt.where(SystemSnapshot.snapshot_type == snapshot_type.value)
        
        stmt = stmt.order_by(SystemSnapshot.created_at.desc()).limit(limit)
        result = self.db.execute(stmt)
        return result.scalars().all()
