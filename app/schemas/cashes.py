from datetime import date as date_type, time as time_type, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict

# ========== CASHES DETAILS ==========

class CashesDetailsBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    description: str = Field(max_length=255)
    amount: float
    date: date_type
    time_transaction: time_type = Field(default_factory=lambda: datetime.now().time())
    service_id: UUID
    cash_id: UUID
    transaction_type: str = Field(default="income", max_length=50)
    reference_id: UUID | None = None
    metadata: dict | None = None
    created_by: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CashesDetailsCreate(CashesDetailsBase):
    pass

class CashesDetailsUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=255)
    amount: Optional[float] = None
    date: Optional[date_type] = None
    time_transaction: Optional[time_type] = None
    service_id: Optional[UUID] = None
    cash_id: Optional[UUID] = None
    transaction_type: Optional[str] = Field(default=None, max_length=50)
    reference_id: Optional[UUID] = None
    metadata: Optional[dict] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

class CashesDetailsRead(CashesDetailsBase):
    id: UUID


# ========== CASHES ==========

class CashesBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    income: float
    expense: float
    date: date_type
    time_transaction: time_type = Field(default_factory=lambda: datetime.now().time())
    balance: float = 0
    transaction_type: str = Field(default="income", max_length=50)
    reference_id: UUID | None = None
    description: str | None = Field(default=None, max_length=255)
    metadata: dict | None = None
    created_by: UUID | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class CashesCreate(CashesBase):
    pass

class CashesUpdate(BaseModel):
    income: Optional[float] = None
    expense: Optional[float] = None
    date: Optional[date_type] = None
    time_transaction: Optional[time_type] = None
    balance: Optional[float] = None
    transaction_type: Optional[str] = Field(default=None, max_length=50)
    reference_id: Optional[UUID] = None
    description: Optional[str] = Field(default=None, max_length=255)
    metadata: Optional[dict] = None
    created_by: Optional[UUID] = None
    created_at: Optional[datetime] = None

class CashesRead(CashesBase):
    id: UUID
    details: Optional[List[CashesDetailsRead]] = None  # Include nested
