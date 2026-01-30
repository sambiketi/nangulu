"""
Dashboard and alert schemas.
Contract: Real-time state reflection, simplicity over cleverness.
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import date, datetime
from decimal import Decimal
from enum import Enum

class AlertLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class AlertType(str, Enum):
    STOCK_LOW = "STOCK_LOW"
    STOCK_CRITICAL = "STOCK_CRITICAL"
    SYSTEM = "SYSTEM"
    PERFORMANCE = "PERFORMANCE"

# Alert Schemas
class AlertBase(BaseModel):
    alert_type: AlertType
    level: AlertLevel
    message: str
    item_id: Optional[int] = None

class AlertCreate(AlertBase):
    pass

class AlertResponse(AlertBase):
    id: int
    created_at: datetime
    acknowledged: bool
    acknowledged_by: Optional[int]
    acknowledged_at: Optional[datetime]

# Stock Dashboard
class StockDashboardItem(BaseModel):
    item_id: int
    name: str
    current_stock: Decimal
    current_price_per_kg: Decimal
    low_stock_level: Decimal
    critical_stock_level: Decimal
    stock_status: str
    stock_value: Decimal
    needs_attention: bool

class StockDashboardResponse(BaseModel):
    items: List[StockDashboardItem]
    total_items: int
    total_stock_value: Decimal
    low_stock_items: int
    critical_stock_items: int

# Sales Dashboard
class DailySalesSummary(BaseModel):
    sale_date: date
    item_name: str
    cashier_name: str
    total_sales: int
    total_kg_sold: Decimal
    total_revenue: Decimal

class SalesDashboardResponse(BaseModel):
    today_sales: List[DailySalesSummary]
    today_total_kg: Decimal
    today_total_revenue: Decimal
    today_transaction_count: int

# Cashier Performance
class CashierPerformanceMetric(BaseModel):
    cashier_id: int
    cashier_name: str
    days_active: int
    total_sales: int
    total_kg_sold: Decimal
    total_revenue: Decimal
    avg_selling_price: Decimal

class PerformanceDashboardResponse(BaseModel):
    cashiers: List[CashierPerformanceMetric]
    period_start: date
    period_end: date

# System Overview
class SystemOverview(BaseModel):
    total_items: int
    active_items: int
    total_stock_kg: Decimal
    total_stock_value: Decimal
    today_sales_count: int
    today_revenue: Decimal
    active_cashiers: int
    pending_alerts: int
    system_status: str

# Dashboard Filters
class DateRangeFilter(BaseModel):
    start_date: date = Field(default_factory=lambda: date.today())
    end_date: date = Field(default_factory=lambda: date.today())
