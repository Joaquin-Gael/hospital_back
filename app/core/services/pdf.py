"""Utilities to render PDF documents for turns using ReportLab."""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, StyleSheet1, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .pdf_data import TurnPdfData, TurnPdfService


@dataclass(frozen=True)
class PdfPalette:
    """Palette defining the colors used in the generated PDF."""

    primary: colors.Color = colors.HexColor("#1F3C88")
    secondary: colors.Color = colors.HexColor("#F2F4FF")
    accent: colors.Color = colors.HexColor("#F47C3C")
    text: colors.Color = colors.HexColor("#1A1A1A")


@dataclass(frozen=True)
class PdfTypography:
    """Typography configuration for titles and body text."""

    title_font: str = "Helvetica-Bold"
    body_font: str = "Helvetica"
    section_font: Optional[str] = None


def _build_styles(typography: PdfTypography, palette: PdfPalette) -> StyleSheet1:
    """Create the style sheet used across the document."""

    styles = getSampleStyleSheet()

    section_font = typography.section_font or typography.title_font

    styles.add(
        ParagraphStyle(
            name="TurnTitle",
            parent=styles["Heading1"],
            fontName=typography.title_font,
            fontSize=18,
            leading=22,
            textColor=palette.primary,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            fontName=section_font,
            fontSize=14,
            leading=18,
            textColor=palette.accent,
            spaceBefore=12,
            spaceAfter=4,
            underlineWidth=1,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyTextOverride",
            parent=styles["BodyText"],
            fontName=typography.body_font,
            fontSize=10,
            leading=14,
            textColor=palette.text,
        )
    )

    styles.add(
        ParagraphStyle(
            name="MetaText",
            parent=styles["BodyText"],
            fontName=typography.body_font,
            fontSize=9,
            leading=12,
            textColor=palette.primary,
        )
    )

    return styles


def _make_table(
    data: Iterable[Iterable[str]],
    palette: PdfPalette,
    *,
    header: bool = False,
    font_name: str = "Helvetica",
    header_font: Optional[str] = None,
) -> Table:
    """Helper that builds a stylised table."""

    table = Table(list(data), hAlign="LEFT")

    style_commands = [
        ("FONTNAME", (0, 0), (-1, -1), font_name),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TEXTCOLOR", (0, 0), (-1, -1), palette.text),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, palette.secondary),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]

    if header:
        style_commands.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), palette.primary),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), header_font or font_name),
                ("FONTSIZE", (0, 0), (-1, 0), 10),
            ]
        )

    table.setStyle(TableStyle(style_commands))
    return table


def _logo_placeholder(width: float, height: float, palette: PdfPalette) -> Table:
    """Return a placeholder block reserved for the logo area."""

    placeholder = Table(
        [[Paragraph("", ParagraphStyle(name="Empty"))]],
        colWidths=width,
        rowHeights=height,
    )
    placeholder.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.5, palette.secondary),
                ("BACKGROUND", (0, 0), (-1, -1), palette.secondary),
            ]
        )
    )
    return placeholder


def _format_service_row(service: TurnPdfService) -> list[str]:
    """Format a service entry to be rendered inside a table."""

    description = service.description or "-"
    specialty = service.specialty or "-"
    return [service.name, specialty, f"$ {service.price:,.2f}", description]


def render_turn_pdf(
    data: TurnPdfData,
    *,
    typography: PdfTypography | None = None,
    palette: PdfPalette | None = None,
    logo_path: str | None = None,
    page_size=A4,
    left_margin: float = 0.7 * inch,
    right_margin: float = 0.7 * inch,
    top_margin: float = inch,
    bottom_margin: float = 0.7 * inch,
) -> bytes:
    """Render a PDF file representing the provided turn data."""

    typography = typography or PdfTypography()
    palette = palette or PdfPalette()

    styles = _build_styles(typography, palette)
    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )

    story: list = []

    # Header with logo and title.
    if logo_path:
        try:
            logo = Image(logo_path, width=1.2 * inch, height=1.2 * inch, kind="proportional")
        except Exception:
            logo = _logo_placeholder(1.2 * inch, 1.2 * inch, palette)
    else:
        logo = _logo_placeholder(1.2 * inch, 1.2 * inch, palette)

    title = Paragraph("Reporte de Turno Médico", styles["TurnTitle"])
    meta_lines = [
        f"Turno: {data.turn_id}",
        f"Estado: {data.state}",
        f"Fecha generado: {data.generated_at}",
    ]
    meta = Paragraph("<br/>".join(meta_lines), styles["MetaText"])

    header = Table(
        [[logo, Paragraph("", styles["BodyTextOverride"]), title, meta]],
        colWidths=[1.2 * inch, 0.2 * inch, 3.2 * inch, 2.4 * inch],
    )
    header.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 0), (0, 0)),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ALIGN", (2, 0), (2, 0), "LEFT"),
                ("ALIGN", (3, 0), (3, 0), "RIGHT"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    story.append(header)
    story.append(Spacer(1, 12))

    # Appointment summary section
    story.append(Paragraph("Resumen del turno", styles["SectionTitle"]))

    summary_rows = [
        ["Motivo", data.reason or "No especificado"],
        ["Fecha programada", data.scheduled_date or "-"],
        ["Hora programada", data.scheduled_time or "-"],
        ["Fecha de creación", data.created_at or "-"],
        ["Fecha límite", data.limit_date or "-"],
        ["ID de cita", data.appointment_id or "-"],
    ]

    summary_table = _make_table(summary_rows, palette, font_name=typography.body_font)
    story.append(summary_table)

    # Patient section
    story.append(Paragraph("Datos del paciente", styles["SectionTitle"]))
    patient_rows = [
        ["Nombre completo", data.patient_full_name],
        ["DNI", data.patient_dni or "-"],
        ["Correo electrónico", data.patient_email or "-"],
        ["Teléfono", data.patient_phone or "-"],
    ]
    story.append(_make_table(patient_rows, palette, font_name=typography.body_font))

    # Doctor section
    story.append(Paragraph("Datos del profesional", styles["SectionTitle"]))
    doctor_rows = [
        ["Nombre", data.doctor_full_name],
        ["Especialidad", data.doctor_specialty or "-"],
    ]
    story.append(_make_table(doctor_rows, palette, font_name=typography.body_font))

    # Services section
    story.append(Paragraph("Servicios asociados", styles["SectionTitle"]))
    if data.services:
        header_row = ["Servicio", "Especialidad", "Precio", "Descripción"]
        table_data = [header_row] + [_format_service_row(service) for service in data.services]
        header_font = typography.section_font or typography.title_font
        services_table = _make_table(
            table_data,
            palette,
            header=True,
            font_name=typography.body_font,
            header_font=header_font,
        )
        story.append(services_table)
    else:
        story.append(Paragraph("No hay servicios asociados al turno.", styles["BodyTextOverride"]))

    # Summary totals
    story.append(Paragraph("Resumen financiero", styles["SectionTitle"]))
    total_table = _make_table(
        [
            ["Servicios", data.services_summary or "Sin servicios"],
            ["Total", f"$ {data.total_price:,.2f}"],
        ],
        palette,
        font_name=typography.body_font,
    )
    story.append(total_table)

    story.append(Spacer(1, 18))
    story.append(
        Paragraph(
            "Documento generado automáticamente por Hospital SDLG.",
            styles["MetaText"],
        )
    )

    doc.build(story)
    return buffer.getvalue()


__all__ = [
    "PdfPalette",
    "PdfTypography",
    "render_turn_pdf",
]