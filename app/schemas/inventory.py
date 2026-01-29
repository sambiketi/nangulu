"""
Inventory schemas following contract:
- KGs as source of truth
- Append-only ledger
- No silent updates
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from enum import Enum

class SourceType(str, Enum):
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    REVERSAL = "REVERSAL"
    SNAPSHOT = "SNAPSHOT"

class StockStatus(str, Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    CRITICAL = "CRITICAL"

# Inventory Item Schemas
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    current_price_per_kg: Decimal = Field(..., gt=0)
    low_stock_level: Decimal = Field(100.000, ge=0)
    critical_stock_level: Decimal = Field(50.000, ge=0)

class InventoryItemCreate(InventoryItemBase):
    pass

class InventoryItemUpdate(BaseModel):
    current_price_per_kg: Optional[Decimal] = Field(None, gt=0)
    low_stock_level: Optional[Decimal] = Field(None, ge=0)
    critical_stock_level: Optional[Decimal] = Field(None, ge=0)
    is_active: Optional[bool] = None

class InventoryItemResponse(InventoryItemBase):
    id: int
    created_by: Optional[int]
    is_active: bool
    created_at: datetime
    updated_at: datetime

# Purchase Schemas (Admin only)
class PurchaseCreate(BaseModel):
    item_id: int = Field(..., gt=0)
    purchase_kg: Decimal = Field(..., gt=0, le=10000)
    cost_per_kg: Decimal = Field(..., gt=0)
    supplier_name: Optional[str] = Field(None, max_length=100)
    notes: Optional[str] = None
    
    @field_validator('purchase_kg')
    @classmethod
    def round_kg(cls, v: Decimal) -> Decimal:
        """Round to 3 decimal places (contract: KG precision)"""
        return round(v, 3)

# Ledger Schemas (Append-only)
class LedgerEntryBase(BaseModel):
    item_id: int
    kg_change: Decimal
    source_type: SourceType
    source_id: Optional[int] = None
    notes: Optional[str] = None

class LedgerEntryCreate(LedgerEntryBase):
    pass

class LedgerEntryResponse(LedgerEntryBase):
    id: int
    created_by: Optional[int]
    created_at: datetime
    item_name: str

# Stock Status
class StockStatusResponse(BaseModel):
    item_id: int
    name: str
    total_kg: Decimal
    current_price_per_kg: Decimal
    low_stock_level: Decimal
    critical_stock_level: Decimal
    stock_status: StockStatus
    stock_value: Decimal

# Conversion
class ConversionRequest(BaseModel):
    item_id: int
    amount: Decimal = Field(..., gt=0)
    is_kg: bool = True  # True = amount is KG, False = amount is price

class ConversionResponse(BaseModel):
    item_id: int
    item_name: str
    kg_amount: Decimal
    price_amount: Decimal
    current_price_per_kg: Decimal
