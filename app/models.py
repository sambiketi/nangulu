from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# ------------------------------
# Users (Admin + Cashiers)
# ------------------------------
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)  # admin / cashier
    is_active = Column(Boolean, default=True)  # soft delete for cashiers
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # FIX: Added relationships for accessing related data
    sales = relationship("Sale", back_populates="cashier", foreign_keys="Sale.cashier_id")
    inventory_ledgers = relationship("InventoryLedger", back_populates="creator", foreign_keys="InventoryLedger.created_by")

# ------------------------------
# Inventory
# ------------------------------
class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    current_price_per_kg = Column(DECIMAL(10,2), nullable=False)  # selling price
    purchase_price_per_kg = Column(DECIMAL(10,2), nullable=True)  # last purchase price
    low_stock_level = Column(DECIMAL(12,3), default=100.000)
    critical_stock_level = Column(DECIMAL(12,3), default=50.000)
    quantity_available = Column(DECIMAL(12,3), default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())
    
    # FIX: Added relationships for accessing related data
    sales = relationship("Sale", back_populates="item")
    inventory_ledgers = relationship("InventoryLedger", back_populates="item")

# ------------------------------
# Sale
# ------------------------------
class Sale(Base):
    __tablename__ = 'sales'
    
    id = Column(Integer, primary_key=True, index=True)
    sale_number = Column(String(20), unique=True)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    kg_sold = Column(DECIMAL(10,3), nullable=False)
    price_per_kg_snapshot = Column(DECIMAL(10,2), nullable=False)
    total_price = Column(DECIMAL(12,2), nullable=False)
    cashier_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    payment_type = Column(String(10), nullable=False)  # Cash / Mpesa
    customer_name = Column(String(100))
    status = Column(String(10), default='ACTIVE')  # ACTIVE / REVERSED
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # FIX: Added relationships for accessing related data
    item = relationship("InventoryItem", back_populates="sales")
    cashier = relationship("User", back_populates="sales", foreign_keys=[cashier_id])

# ------------------------------
# Sale Reversal
# ------------------------------
class SaleReversal(Base):
    __tablename__ = 'sale_reversals'
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), unique=True, nullable=False)
    reversed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    reversal_reason = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

# ------------------------------
# Inventory Ledger
# ------------------------------
class InventoryLedger(Base):
    __tablename__ = 'inventory_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    kg_change = Column(DECIMAL(12,3), nullable=False)
    source_type = Column(String(20))  # sale / purchase / reversal
    source_id = Column(Integer)  # sale_id or purchase_id
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP, server_default=func.now())
    
    # FIX: Added relationships for accessing related data
    item = relationship("InventoryItem", back_populates="inventory_ledgers")
    creator = relationship("User", back_populates="inventory_ledgers", foreign_keys=[created_by])