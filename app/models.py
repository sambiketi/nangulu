from sqlalchemy import Column, Integer, String, DECIMAL, Boolean, ForeignKey, Text, TIMESTAMP
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class InventoryItem(Base):
    __tablename__ = 'inventory_items'
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    current_price_per_kg = Column(DECIMAL(10, 2), nullable=False)
    low_stock_level = Column(DECIMAL(12, 3), default=100.000)
    critical_stock_level = Column(DECIMAL(12, 3), default=50.000)
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class Sale(Base):
    __tablename__ = 'sales'
    
    id = Column(Integer, primary_key=True, index=True)
    sale_number = Column(String(20), unique=True)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    kg_sold = Column(DECIMAL(10, 3), nullable=False)
    price_per_kg_snapshot = Column(DECIMAL(10, 2), nullable=False)
    total_price = Column(DECIMAL(12, 2))
    cashier_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    customer_name = Column(String(100))
    status = Column(String(10), default='ACTIVE')
    created_at = Column(TIMESTAMP, server_default=func.now())

class SaleReversal(Base):
    __tablename__ = 'sale_reversals'
    
    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey('sales.id'), unique=True, nullable=False)
    reversed_by = Column(Integer, ForeignKey('users.id'), nullable=False)
    reversal_reason = Column(Text, nullable=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

class InventoryLedger(Base):
    __tablename__ = 'inventory_ledger'
    
    id = Column(Integer, primary_key=True, index=True)
    item_id = Column(Integer, ForeignKey('inventory_items.id'), nullable=False)
    kg_change = Column(DECIMAL(12, 3), nullable=False)
    source_type = Column(String(20))
    source_id = Column(Integer)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(TIMESTAMP, server_default=func.now())

class AuditLog(Base):
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String(50), nullable=False)
    table_name = Column(String(50))
    record_id = Column(Integer)
    old_values = Column(Text)
    new_values = Column(Text)
    ip_address = Column(String(50))
    user_agent = Column(Text)
    performed_at = Column(TIMESTAMP, server_default=func.now())
    notes = Column(Text)

class CashierSession(Base):
    __tablename__ = 'cashier_sessions'
    
    id = Column(Integer, primary_key=True, index=True)
    cashier_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    session_start = Column(TIMESTAMP, server_default=func.now())
    session_end = Column(TIMESTAMP)
    is_active = Column(Boolean, default=True)
