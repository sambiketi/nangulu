"""
SQLAlchemy models matching the provided database schema exactly.
No modifications, no additions - strict schema compliance.
"""
from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import JSONB, INET
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.sql import func
from decimal import Decimal

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    role = Column(String(20), nullable=False, default='cashier')
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    created_items = relationship("InventoryItem", back_populates="creator")
    sales_as_cashier = relationship("Sale", back_populates="cashier")
    reversals = relationship("SaleReversal", back_populates="reverser")
    ledger_entries = relationship("InventoryLedger", back_populates="creator_rel")
    audit_logs = relationship("AuditLog", back_populates="user_rel")

class InventoryItem(Base):
    __tablename__ = "inventory_items"
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    current_price_per_kg = Column(Numeric(10, 2), nullable=False)
    low_stock_level = Column(Numeric(12, 3), default=Decimal('100.000'))
    critical_stock_level = Column(Numeric(12, 3), default=Decimal('50.000'))
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    is_active = Column(Boolean, default=True)
    
    # Relationships
    creator = relationship("User", back_populates="created_items")
    sales = relationship("Sale", back_populates="item")
    ledger_entries = relationship("InventoryLedger", back_populates="item")

class Sale(Base):
    __tablename__ = "sales"
    
    id = Column(Integer, primary_key=True)
    sale_number = Column(String(20), unique=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    kg_sold = Column(Numeric(10, 3), nullable=False)
    price_per_kg_snapshot = Column(Numeric(10, 2), nullable=False)
    total_price = Column(Numeric(12, 2))
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    customer_name = Column(String(100))
    status = Column(String(10), default='ACTIVE')
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    item = relationship("InventoryItem", back_populates="sales")
    cashier = relationship("User", back_populates="sales_as_cashier")
    reversal = relationship("SaleReversal", uselist=False, back_populates="sale")

class SaleReversal(Base):
    __tablename__ = "sale_reversals"
    
    id = Column(Integer, primary_key=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), unique=True, nullable=False)
    reversed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    reversal_reason = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    sale = relationship("Sale", back_populates="reversal")
    reverser = relationship("User", back_populates="reversals")

class InventoryLedger(Base):
    __tablename__ = "inventory_ledger"
    
    id = Column(Integer, primary_key=True)
    item_id = Column(Integer, ForeignKey("inventory_items.id"), nullable=False)
    kg_change = Column(Numeric(12, 3), nullable=False)
    source_type = Column(String(20))
    source_id = Column(Integer)
    notes = Column(Text)
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    item = relationship("InventoryItem", back_populates="ledger_entries")
    creator_rel = relationship("User", back_populates="ledger_entries")

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String(50), nullable=False)
    table_name = Column(String(50))
    record_id = Column(Integer)
    old_values = Column(JSONB)
    new_values = Column(JSONB)
    ip_address = Column(INET)
    user_agent = Column(Text)
    performed_at = Column(DateTime(timezone=True), server_default=func.now())
    notes = Column(Text)
    
    # Relationships
    user_rel = relationship("User", back_populates="audit_logs")

class CashierSession(Base):
    __tablename__ = "cashier_sessions"
    
    id = Column(Integer, primary_key=True)
    cashier_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_start = Column(DateTime(timezone=True), server_default=func.now())
    session_end = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    
    # Relationship
    cashier = relationship("User")
