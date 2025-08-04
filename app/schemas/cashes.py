from datetime import date as date_type, time as time_type, datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field

# ========== CASHES DETAILS ==========

class CashesDetailsBase(BaseModel):
    description: str = Field(max_length=50)
    amount: float
    date: date_type
    time_transaction: time_type = Field(default_factory=lambda: datetime.now().time())
    service_id: UUID
    cash_id: UUID

class CashesDetailsCreate(CashesDetailsBase):
    pass

class CashesDetailsUpdate(BaseModel):
    description: Optional[str] = Field(default=None, max_length=50)
    amount: Optional[float] = None
    date: Optional[date_type] = None
    time_transaction: Optional[time_type] = None
    service_id: Optional[UUID] = None
    cash_id: Optional[UUID] = None

class CashesDetailsRead(CashesDetailsBase):
    id: UUID


# ========== CASHES ==========

class CashesBase(BaseModel):
    income: float
    expense: float
    date: date_type
    time_transaction: time_type = Field(default_factory=lambda: datetime.now().time())
    balance: float = 0
    appointment_id: UUID

class CashesCreate(CashesBase):
    pass

class CashesUpdate(BaseModel):
    income: Optional[float] = None
    expense: Optional[float] = None
    date: Optional[date_type] = None
    time_transaction: Optional[time_type] = None
    balance: Optional[float] = None
    appointment_id: Optional[UUID] = None

class CashesRead(CashesBase):
    id: UUID
    details: Optional[List[CashesDetailsRead]] = None  # Include nested
