from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

# ------------------------------
# User Schemas (Admin + Cashiers)
# ------------------------------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., pattern="^(admin|cashier)$")  # <-- changed from regex

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None
    role: Optional[str] = Field(None, pattern="^(admin|cashier)$")  # <-- changed
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Inventory Schemas
# ------------------------------
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    current_price_per_kg: Decimal = Field(..., gt=0)
    quantity_available: Decimal = Field(default=0, ge=0)
    low_stock_level: Decimal = Field(default=100.0, gt=0)
    critical_stock_level: Decimal = Field(default=50.0, gt=0)

class InventoryItemCreate(InventoryItemBase):
    purchase_price_per_kg: Decimal = Field(..., gt=0)

class InventoryItemUpdate(BaseModel):
    current_price_per_kg: Optional[Decimal] = None
    purchase_price_per_kg: Optional[Decimal] = None
    quantity_available: Optional[Decimal] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class InventoryItemResponse(InventoryItemBase):
    id: int
    purchase_price_per_kg: Optional[Decimal]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Sale Schemas (Cashier)
# ------------------------------
class SaleCreate(BaseModel):
    item_id: int
    kg_sold: Decimal = Field(..., gt=0)
    payment_type: str = Field(..., pattern="^(Cash|Mpesa)$")  # <-- changed from regex
    customer_name: Optional[str] = None

class SaleResponse(BaseModel):
    id: int
    sale_number: str
    item_id: int
    kg_sold: Decimal
    price_per_kg_snapshot: Decimal
    total_price: Decimal
    cashier_id: int
    payment_type: str
    customer_name: Optional[str]
    status: str
    created_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Sale Reversal Schemas
# ------------------------------
class SaleReversalCreate(BaseModel):
    sale_id: int
    reversal_reason: str = Field(..., min_length=5)

class SaleReversalResponse(BaseModel):
    id: int
    sale_id: int
    reversed_by: int
    reversal_reason: str
    created_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Inventory Ledger Schemas
# ------------------------------
class InventoryLedgerBase(BaseModel):
    item_id: int
    kg_change: Decimal
    source_type: str
    source_id: Optional[int]
    notes: Optional[str]
    created_by: int

class InventoryLedgerResponse(InventoryLedgerBase):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Admin Purchase / Add Stock Schemas
# ------------------------------
class PurchaseCreate(BaseModel):
    item_id: Optional[int]  # if existing item, else create new
    name: Optional[str]
    description: Optional[str] = None
    kg_added: Decimal = Field(..., gt=0)
    purchase_price_per_kg: Decimal = Field(..., gt=0)

class PurchaseResponse(BaseModel):
    id: int
    item_id: int
    kg_added: Decimal
    purchase_price_per_kg: Decimal
    created_by: int
    created_at: datetime

    class Config:
        orm_mode = True

# ------------------------------
# Login / Auth Schemas
# ------------------------------
class UserLogin(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    message: str
    user_id: int
    username: str
    full_name: str
    role: str
    redirect_to: str

# ------------------------------
# Optional: Ledger Filter / Query
# ------------------------------
class LedgerQuery(BaseModel):
    item_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    source_type: Optional[str] = None
