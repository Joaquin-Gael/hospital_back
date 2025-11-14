from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import List, Optional, Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import ORJSONResponse

from app.audit import AuditAction, AuditEventRead, AuditRepository, AuditTargetType
from app.core.auth import JWTBearer
from app.db.main import SessionDep
from app.config import (
    AUDIT_ENABLED,
    AUDIT_EXPORT_DEFAULT_LIMIT,
    AUDIT_EXPORT_MAX_LIMIT,
    AUDIT_LIST_DEFAULT_LIMIT,
    AUDIT_LIST_MAX_LIMIT,
)


auth = JWTBearer()

router = APIRouter(
    prefix="/audit",
    tags=["audit"],
    dependencies=[Depends(auth)],
    include_in_schema=AUDIT_ENABLED,
)


def _ensure_admin(request: Request) -> None:
    if not AUDIT_ENABLED:
        raise HTTPException(status_code=503, detail="Audit trail disabled")

    user = getattr(request.state, "user", None)
    scopes = set(getattr(request.state, "scopes", []) or [])
    if not user or ("admin" not in scopes and not getattr(user, "is_superuser", False)):
        raise HTTPException(status_code=403, detail="Not authorized")


def _serialize(events: List[AuditEventRead]) -> List[dict]:
    return [event.model_dump() for event in events]

def _format_request(
    actor_id: Optional[UUID] = Query(None),
    action: Optional[AuditAction] = Query(None),
    target_type: Optional[AuditTargetType] = Query(None),
    occurred_after: Optional[datetime] = Query(None, alias="from"),
    occurred_before: Optional[datetime] = Query(None, alias="to"),
    limit: int = Query(AUDIT_EXPORT_DEFAULT_LIMIT, ge=1, le=AUDIT_EXPORT_MAX_LIMIT),
):
    return {
        "actor_id": actor_id,
        "action": action,
        "target_type": target_type,
        "occurred_after": occurred_after,
        "occurred_before": occurred_before,
        "limit": limit,
    }


@router.get("/", response_model=List[AuditEventRead])
async def list_audit_events(
    request: Request,
    session: SessionDep,
    audit_parameters: Annotated[dict, Depends(_format_request)],
):
    _ensure_admin(request)

    repo = AuditRepository(session)
    events = [
        AuditEventRead.model_validate(event)
        for event in repo.list(**audit_parameters)
    ]
    return ORJSONResponse(_serialize(events))


@router.get("/export")
async def export_audit_events(
    request: Request,
    session: SessionDep,
    audit_parameters: Annotated[dict, Depends(_format_request)],
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    _ensure_admin(request)

    repo = AuditRepository(session)
    events = [
        AuditEventRead.model_validate(event)
        for event in repo.list(**audit_parameters)
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
