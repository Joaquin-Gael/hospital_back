"""Utilities for generating and persisting PDF documents for turns."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
from uuid import UUID

from sqlmodel import Session, select

import pymupdf as fitz

from app.core.services.pdf_data import build_turn_pdf_data
from app.core.services.storage import load_pdf_file, save_pdf_file
from app.models import TurnDocument, TurnDocumentDownload, Turns


def _build_filename(turn: Turns) -> str:
    return f"turn_{turn.id}.pdf"


def _default_subdir(turn: Turns) -> Optional[str]:
    user_id = getattr(turn, "user_id", None)
    return str(user_id) if user_id else None


def _render_turn_pdf(turn: Turns) -> bytes:
    data = build_turn_pdf_data(turn)

    doc = fitz.open()
    try:
        page = doc.new_page()
        margin_left = 72
        margin_top = 72
        line_height = 16

        def write(text: str, *, offset: int) -> None:
            page.insert_text((margin_left, margin_top + offset * line_height), text)

        write(f"Comprobante de turno #{data.turn_id}", offset=0)
        write(f"Generado: {data.generated_at}", offset=1)
        write("--- Paciente ---", offset=3)
        write(f"Nombre: {data.patient_full_name}", offset=4)
        if data.patient_dni:
            write(f"DNI: {data.patient_dni}", offset=5)
        if data.patient_phone:
            write(f"Teléfono: {data.patient_phone}", offset=6)
        if data.patient_email:
            write(f"Email: {data.patient_email}", offset=7)

        offset = 9
        write("--- Profesional ---", offset=offset)
        offset += 1
        write(f"Nombre: {data.doctor_full_name}", offset=offset)
        offset += 1
        if data.doctor_specialty:
            write(f"Especialidad: {data.doctor_specialty}", offset=offset)
            offset += 1

        write("--- Turno ---", offset=offset)
        offset += 1
        write(f"Estado: {data.state}", offset=offset)
        offset += 1
        if data.reason:
            write(f"Motivo: {data.reason}", offset=offset)
            offset += 1
        write(f"Fecha: {data.scheduled_date}", offset=offset)
        offset += 1
        write(f"Hora: {data.scheduled_time}", offset=offset)
        offset += 1
        if data.limit_date:
            write(f"Válido hasta: {data.limit_date}", offset=offset)
            offset += 1
        if data.appointment_id:
            write(f"Cita asociada: {data.appointment_id}", offset=offset)
            offset += 1

        write("--- Servicios ---", offset=offset)
        offset += 1
        if data.services:
            for service in data.services:
                write(
                    f"• {service.name} ($ {service.price:.2f})",
                    offset=offset,
                )
                offset += 1
                if service.description:
                    write(f"  {service.description}", offset=offset)
                    offset += 1
        else:
            write("Sin servicios asociados", offset=offset)
            offset += 1

        write(f"Total a abonar: $ {data.total_price:.2f}", offset=offset + 1)

        pdf_bytes = doc.tobytes()
    finally:
        doc.close()

    return pdf_bytes


def get_or_create_turn_document(
    session: Session,
    turn: Turns,
    *,
    storage_subdir: Optional[str | Path] = None,
) -> Tuple[TurnDocument, bytes, bool]:
    statement = select(TurnDocument).where(TurnDocument.turn_id == turn.id)
    document = session.exec(statement).first()

    if document is not None:
        try:
            pdf_bytes = load_pdf_file(document.file_path)
            return document, pdf_bytes, False
        except FileNotFoundError:
            pass

    pdf_bytes = _render_turn_pdf(turn)
    filename = _build_filename(turn)
    relative_path = save_pdf_file(
        filename,
        pdf_bytes,
        subdir=storage_subdir or _default_subdir(turn),
    )

    if document is None:
        document = TurnDocument(
            turn_id=turn.id,
            user_id=turn.user_id,
            file_path=relative_path,
            generated_at=datetime.now(),
        )
        session.add(document)
    else:
        document.file_path = relative_path
        document.generated_at = datetime.now()

    session.commit()
    session.refresh(document)

    return document, pdf_bytes, True


def register_turn_document_download(
    session: Session,
    *,
    document: TurnDocument,
    user_id: UUID,
    channel: Optional[str] = None,
    client_ip: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> TurnDocumentDownload:
    normalized_channel = (channel or "api").strip() or "api"

    download = TurnDocumentDownload(
        turn_document_id=document.id,
        turn_id=document.turn_id,
        user_id=user_id,
        channel=normalized_channel[:64],
        client_ip=client_ip,
        user_agent=user_agent[:512] if user_agent else None,
    )

    session.add(download)
    session.commit()
    session.refresh(download)

    return download


__all__ = [
    "get_or_create_turn_document",
    "register_turn_document_download",
]
