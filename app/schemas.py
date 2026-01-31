from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# ------------------------------
# User Schemas
# ------------------------------
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    full_name: str = Field(..., min_length=2, max_length=100)
    role: str = Field(..., pattern="^(admin|cashier)$")

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ------------------------------
# Inventory Schemas
# ------------------------------
class InventoryItemBase(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    current_price_per_kg: Decimal = Field(..., gt=0)
    low_stock_level: Decimal = Field(default=100.000, gt=0)
    critical_stock_level: Decimal = Field(default=50.000, gt=0)
    quantity_available: Decimal = Field(default=0, ge=0)  # Added for tracking stock

class InventoryItemResponse(InventoryItemBase):
    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ------------------------------
# Sale Schemas
# ------------------------------
class SaleCreate(BaseModel):
    item_id: int
    kg_sold: Decimal = Field(..., gt=0)
    customer_name: Optional[str] = None

class SaleResponse(BaseModel):
    id: int
    sale_number: str
    item_id: int
    kg_sold: Decimal
    price_per_kg_snapshot: Decimal
    total_price: Decimal
    cashier_id: int
    cashier_name: Optional[str]  # Added for admin sales dashboard
    customer_name: Optional[str]
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True

# ------------------------------
# Login Response
# ------------------------------
class LoginResponse(BaseModel):
    message: str
    user_id: int
    username: str
    full_name: str
    role: str
    redirect_to: str

# ------------------------------
# Additional / Admin Schemas
# ------------------------------
# Inventory movement response (simplified)
class InventoryMovementResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    quantity_available: Decimal
    current_price_per_kg: Decimal
    low_stock_level: Decimal
    critical_stock_level: Decimal
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
