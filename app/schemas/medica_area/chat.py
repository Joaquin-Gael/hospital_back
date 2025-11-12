from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel


class MessageBase(BaseModel):
    id: UUID
    content: str
    created_at: datetime
    deleted_at: datetime


class MessageResponse(MessageBase):
    sender: Optional["DoctorResponse"] = None
    chat: Optional["ChatResponse"] = None


class ChatBase(BaseModel):
    id: UUID


class ChatResponse(ChatBase):
    doc_2: Optional["DoctorResponse"] = None
    doc_1: Optional["DoctorResponse"] = None
    messages: Optional[List[MessageResponse]] = None
