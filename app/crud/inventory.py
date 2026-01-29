"""
Inventory CRUD operations with contract enforcement:
- KGs as source of truth
- Append-only ledger
- Atomic transactions
- No silent updates
"""
from sqlalchemy import select, insert, update, delete, func
from sqlalchemy.exc import SQLAlchemyError, IntegrityError, OperationalError
from sqlalchemy.orm import Session, selectinload
import logging
from typing import List, Optional, Tuple, Dict, Any
from decimal import Decimal

from app.models import InventoryItem, InventoryLedger, User, Sale
from app.crud.base import CRUDBase
from app.schemas.inventory import PurchaseCreate, InventoryItemCreate, InventoryItemUpdate

logger = logging.getLogger(__name__)

class CRUDInventoryItem(CRUDBase[InventoryItem]):
    def __init__(self):
        super().__init__(InventoryItem)
    
    def get_by_name(self, db: Session, name: str) -> Optional[InventoryItem]:
        """Get inventory item by name"""
        try:
            stmt = select(InventoryItem).where(InventoryItem.name == name)
            result = db.execute(stmt)
            return result.scalar_one_or_none()
        except SQLAlchemyError as e:
            logger.error(f"Error getting inventory item by name {name}: {e}")
            return None
    
    def create_with_creator(self, db: Session, *, obj_in: InventoryItemCreate, creator_id: int) -> Optional[InventoryItem]:
        """Create inventory item with creator (admin only)"""
        try:
            # Contract: Items created only when admin records a purchase
            # This method is called from purchase creation flow
            item_data = obj_in.model_dump()
            item_data["created_by"] = creator_id
            
            stmt = insert(InventoryItem).values(**item_data).returning(InventoryItem)
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating inventory item: {e}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating inventory item: {e}")
            return None
    
    def update_price(self, db: Session, *, id: int, new_price: Decimal, updated_by: int) -> Optional[InventoryItem]:
        """Update price per kg (admin only)"""
        try:
            stmt = (
                update(InventoryItem)
                .where(InventoryItem.id == id)
                .values(current_price_per_kg=new_price)
                .returning(InventoryItem)
            )
            result = db.execute(stmt)
            db.commit()
            item = result.scalar_one()
            
            # Contract: Price changes affect future sales only
            # No need to update existing sales (price snapshotted)
            return item
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error updating inventory item price {id}: {e}")
            return None
    
    def get_active_items(self, db: Session, *, skip: int = 0, limit: int = 100) -> List[InventoryItem]:
        """Get all active inventory items"""
        try:
            stmt = (
                select(InventoryItem)
                .where(InventoryItem.is_active == True)
                .order_by(InventoryItem.name)
                .offset(skip)
                .limit(limit)
            )
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting active inventory items: {e}")
            return []

class CRUDInventoryLedger(CRUDBase[InventoryLedger]):
    def __init__(self):
        super().__init__(InventoryLedger)
    
    def create_ledger_entry(self, db: Session, *, obj_in: Dict[str, Any]) -> Optional[InventoryLedger]:
        """Create ledger entry (append-only)"""
        try:
            stmt = insert(InventoryLedger).values(**obj_in).returning(InventoryLedger)
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating ledger entry: {e}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating ledger entry: {e}")
            return None
    
    def get_item_stock(self, db: Session, item_id: int) -> Decimal:
        """Calculate current stock for item (SUM of ledger kg_change)"""
        try:
            stmt = select(func.coalesce(func.sum(InventoryLedger.kg_change), 0)).where(
                InventoryLedger.item_id == item_id
            )
            result = db.execute(stmt)
            stock = result.scalar_one()
            return Decimal(str(stock)).quantize(Decimal('0.001'))  # 3 decimal precision
        except SQLAlchemyError as e:
            logger.error(f"Error calculating stock for item {item_id}: {e}")
            return Decimal('0')
    
    def get_item_ledger(self, db: Session, item_id: int, *, skip: int = 0, limit: int = 100) -> List[InventoryLedger]:
        """Get ledger entries for specific item"""
        try:
            stmt = (
                select(InventoryLedger)
                .where(InventoryLedger.item_id == item_id)
                .order_by(InventoryLedger.created_at.desc())
                .offset(skip)
                .limit(limit)
            )
            result = db.execute(stmt)
            return result.scalars().all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting ledger for item {item_id}: {e}")
            return []
    
    def create_purchase_entry(self, db: Session, *, purchase_data: PurchaseCreate, user_id: int) -> Tuple[Optional[InventoryLedger], Optional[InventoryItem]]:
        """
        Create purchase ledger entry (admin only)
        Contract: Items created when admin records purchase
        """
        try:
            # Start transaction
            db.begin()
            
            # Check if item exists
            stmt = select(InventoryItem).where(InventoryItem.id == purchase_data.item_id)
            result = db.execute(stmt)
            item = result.scalar_one_or_none()
            
            if not item:
                # Contract: Create item if it doesn't exist
                item_data = {
                    "name": f"Item_{purchase_data.item_id}",  # Temp name, admin should update
                    "description": f"Auto-created from purchase",
                    "current_price_per_kg": purchase_data.cost_per_kg * Decimal('1.5'),  # 50% markup default
                    "low_stock_level": Decimal('100.000'),
                    "critical_stock_level": Decimal('50.000'),
                    "created_by": user_id,
                    "is_active": True
                }
                
                # Generate unique name
                counter = 1
                while True:
                    test_name = f"Item_{purchase_data.item_id}_{counter}"
                    check_stmt = select(InventoryItem).where(InventoryItem.name == test_name)
                    if not db.execute(check_stmt).scalar_one_or_none():
                        item_data["name"] = test_name
                        break
                    counter += 1
                
                item_stmt = insert(InventoryItem).values(**item_data).returning(InventoryItem)
                item_result = db.execute(item_stmt)
                item = item_result.scalar_one()
            
            # Create ledger entry for purchase
            ledger_data = {
                "item_id": item.id,
                "kg_change": purchase_data.purchase_kg,
                "source_type": "PURCHASE",
                "notes": f"Purchase: {purchase_data.supplier_name or 'No supplier'} - {purchase_data.notes or ''}",
                "created_by": user_id
            }
            
            ledger_stmt = insert(InventoryLedger).values(**ledger_data).returning(InventoryLedger)
            ledger_result = db.execute(ledger_stmt)
            ledger_entry = ledger_result.scalar_one()
            
            db.commit()
            return ledger_entry, item
            
        except IntegrityError as e:
            db.rollback()
            logger.error(f"Integrity error creating purchase: {e}")
            raise
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating purchase: {e}")
            return None, None
    
    def create_sale_entry(self, db: Session, *, item_id: int, kg_sold: Decimal, sale_id: int, user_id: int) -> Optional[InventoryLedger]:
        """Create sale ledger entry (-kg)"""
        try:
            ledger_data = {
                "item_id": item_id,
                "kg_change": -kg_sold,  # Negative for sale
                "source_type": "SALE",
                "source_id": sale_id,
                "notes": f"Sale transaction",
                "created_by": user_id
            }
            
            stmt = insert(InventoryLedger).values(**ledger_data).returning(InventoryLedger)
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating sale ledger entry: {e}")
            return None
    
    def create_reversal_entry(self, db: Session, *, item_id: int, kg_returned: Decimal, reversal_id: int, user_id: int) -> Optional[InventoryLedger]:
        """Create reversal ledger entry (+kg)"""
        try:
            ledger_data = {
                "item_id": item_id,
                "kg_change": kg_returned,  # Positive for reversal
                "source_type": "REVERSAL",
                "source_id": reversal_id,
                "notes": f"Sale reversal",
                "created_by": user_id
            }
            
            stmt = insert(InventoryLedger).values(**ledger_data).returning(InventoryLedger)
            result = db.execute(stmt)
            db.commit()
            return result.scalar_one()
        except SQLAlchemyError as e:
            db.rollback()
            logger.error(f"Error creating reversal ledger entry: {e}")
            return None

# Create instances
crud_inventory_item = CRUDInventoryItem()
crud_inventory_ledger = CRUDInventoryLedger()
