from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import ORJSONResponse

from app.audit import AuditAction, AuditEventRead, AuditRepository, AuditTargetType
from app.core.auth import JWTBearer
from app.db.main import SessionDep
from app.config import (
    audit_enabled,
    audit_export_default_limit,
    audit_export_max_limit,
    audit_list_default_limit,
    audit_list_max_limit,
)


auth = JWTBearer()

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth)],
    include_in_schema=audit_enabled,
)


def _ensure_admin(request: Request) -> None:
    if not audit_enabled:
        raise HTTPException(status_code=503, detail="Audit trail disabled")

    user = getattr(request.state, "user", None)
    scopes = set(getattr(request.state, "scopes", []) or [])
    if not user or ("admin" not in scopes and not getattr(user, "is_superuser", False)):
        raise HTTPException(status_code=403, detail="Not authorized")


def _serialize(events: List[AuditEventRead]) -> List[dict]:
    return [event.model_dump() for event in events]


@router.get("/", response_model=List[AuditEventRead])
async def list_audit_events(
    request: Request,
    session: SessionDep,
    actor_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    target_type: Optional[AuditTargetType] = Query(None),
    occurred_after: Optional[datetime] = Query(None, alias="from"),
    occurred_before: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(audit_list_default_limit, ge=1, le=audit_list_max_limit),
):
    _ensure_admin(request)

    repo = AuditRepository(session)
    events = [
        AuditEventRead.model_validate(event)
        for event in repo.list(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            limit=limit,
        )
    ]
    return ORJSONResponse(_serialize(events))


@router.get("/export")
async def export_audit_events(
    request: Request,
    session: SessionDep,
    actor_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    target_type: Optional[AuditTargetType] = Query(None),
    occurred_after: Optional[datetime] = Query(None, alias="from"),
    occurred_before: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(audit_export_default_limit, ge=1, le=audit_export_max_limit),
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    _ensure_admin(request)

    repo = AuditRepository(session)
    events = [
        AuditEventRead.model_validate(event)
        for event in repo.list(
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            occurred_after=occurred_after,
            occurred_before=occurred_before,
            limit=limit,
        )
    ]

    if format == "json":
        return ORJSONResponse(_serialize(events))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "id",
            "occurred_at",
            "recorded_at",
            "action",
            "severity",
            "target_type",
            "target_id",
            "actor_id",
            "request_id",
            "details",
        ]
    )
    for event in events:
        writer.writerow(
            [
                str(event.id),
                event.occurred_at.isoformat(),
                event.recorded_at.isoformat(),
                event.action.value,
                event.severity.value,
                event.target_type.value,
                str(event.target_id) if event.target_id else "",
                str(event.actor_id) if event.actor_id else "",
                event.request_id or "",
                event.details,
            ]
        )

    filename = "audit-events.csv"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
    }
    return Response(content=output.getvalue(), media_type="text/csv", headers=headers)


__all__ = ["router"]
