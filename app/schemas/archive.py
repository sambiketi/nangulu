"""
Archive and snapshot schemas.
Contract: No silent deletes, corrections via reversals only.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

class ArchiveAction(str, Enum):
    RESET = "RESET"
    SNAPSHOT = "SNAPSHOT"
    RESTORE = "RESTORE"

class ArchiveStatus(str, Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

class SnapshotType(str, Enum):
    FULL_SYSTEM = "FULL_SYSTEM"
    SALES_ONLY = "SALES_ONLY"
    INVENTORY_ONLY = "INVENTORY_ONLY"

# Archive Request Schemas
class ArchiveBase(BaseModel):
    action: ArchiveAction
    snapshot_type: Optional[SnapshotType] = None
    description: str = Field(..., min_length=1, max_length=500)
    retain_days: int = Field(30, ge=1, le=365)  # Default 30 days retention

class ArchiveCreate(ArchiveBase):
    pass

class ArchiveRequest(ArchiveBase):
    confirm_password: str = Field(..., description="Admin password confirmation for destructive operations")

# Archive Response Schemas
class ArchiveRecord(BaseModel):
    id: int
    action: ArchiveAction
    snapshot_type: Optional[SnapshotType]
    description: str
    status: ArchiveStatus
    performed_by: int
    performed_by_name: str
    records_affected: Optional[int]
    file_path: Optional[str]
    file_size: Optional[int]
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]

class ArchiveSummary(BaseModel):
    total_archives: int
    pending_operations: int
    last_snapshot: Optional[datetime]
    total_storage_used: int  # bytes
    oldest_record_date: Optional[date]

# Snapshot Data Schemas
class SystemSnapshot(BaseModel):
    timestamp: datetime
    snapshot_type: SnapshotType
    inventory_summary: Dict[str, Any]
    sales_summary: Dict[str, Any]
    users_summary: Dict[str, Any]
    metadata: Dict[str, Any]

# Reset Confirmation
class ResetConfirmation(BaseModel):
    confirmation_code: str = Field(..., description="Type 'RESET-{date}' to confirm")
    backup_first: bool = True
    reason: str = Field(..., min_length=10, max_length=500)
