"""
Jackdaw Sentry - PDF Investigation Report Generator
Uses reportlab to produce a structured PDF for investigation export.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone


def generate_investigation_pdf(
    investigation: Dict[str, Any],
    evidence: List[Dict[str, Any]],
    narrative: Optional[str] = None,
) -> bytes:
    """Generate a PDF byte string for the given investigation.

    Args:
        investigation: Investigation node properties dict.
        evidence: List of Evidence node property dicts.

    Returns:
        Raw PDF bytes suitable for a StreamingResponse.

    Raises:
        ImportError: If reportlab is not installed.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
        HRFlowable,
    )
    import io

    buffer = io.BytesIO()

    # Page-number callback
    def _add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        page_num = canvas.getPageNumber()
        canvas.setFillColorRGB(0.4, 0.4, 0.4)
        canvas.drawRightString(
            A4[0] - 2 * cm,
            1.2 * cm,
            f"CONFIDENTIAL — Page {page_num}",
        )
        canvas.restoreState()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2.5 * cm,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=18,
        spaceAfter=12,
        textColor=colors.HexColor("#1a202c"),
    )
    heading2_style = ParagraphStyle(
        "Heading2",
        parent=styles["Heading2"],
        fontSize=13,
        spaceBefore=12,
        spaceAfter=6,
        textColor=colors.HexColor("#2d3748"),
    )
    body_style = styles["BodyText"]
    label_style = ParagraphStyle(
        "Label",
        parent=body_style,
        fontName="Helvetica-Bold",
    )

    elements = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Header
    inv_id = investigation.get("investigation_id", "N/A")
    elements.append(Paragraph(f"Investigation Report: {inv_id}", title_style))
    elements.append(Paragraph(f"<i>Generated: {now}</i>", body_style))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Spacer(1, 0.4 * cm))

    # Summary table
    elements.append(Paragraph("Summary", heading2_style))
    summary_data = [
        ["Field", "Value"],
        ["Title", str(investigation.get("title", ""))],
        ["Status", str(investigation.get("status", ""))],
        ["Priority", str(investigation.get("priority", ""))],
        ["Blockchain", str(investigation.get("blockchain", ""))],
        ["Created By", str(investigation.get("created_by", ""))],
        ["Created At", str(investigation.get("created_at", ""))],
        ["Risk Score", str(investigation.get("risk_score", 0.0))],
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm, 13 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f7fafc")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 0.4 * cm))

    # Description
    description = investigation.get("description", "")
    if description:
        elements.append(Paragraph("Description", heading2_style))
        elements.append(Paragraph(str(description), body_style))
        elements.append(Spacer(1, 0.3 * cm))

    # Addresses
    addresses = investigation.get("addresses", [])
    if addresses:
        elements.append(Paragraph("Monitored Addresses", heading2_style))
        addr_data = [["#", "Address"]] + [
            [str(i + 1), str(addr)] for i, addr in enumerate(addresses)
        ]
        addr_table = Table(addr_data, colWidths=[1 * cm, 16 * cm])
        addr_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 5),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
        ]))
        elements.append(addr_table)
        elements.append(Spacer(1, 0.4 * cm))

    # Evidence
    if evidence:
        elements.append(Paragraph(f"Evidence ({len(evidence)} items)", heading2_style))
        evd_data = [["ID", "Type", "Description", "Confidence", "Added By", "Date"]]
        for ev in evidence:
            evd_data.append([
                str(ev.get("evidence_id", ""))[:12],
                str(ev.get("evidence_type", "")),
                str(ev.get("description", ""))[:60],
                f"{float(ev.get('confidence', 0)):.0%}",
                str(ev.get("added_by", "")),
                str(ev.get("added_at", ""))[:10],
            ])
        evd_table = Table(
            evd_data,
            colWidths=[2 * cm, 2.5 * cm, 6 * cm, 2 * cm, 2.5 * cm, 2 * cm],
        )
        evd_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2d3748")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#edf2f7")]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
            ("PADDING", (0, 0), (-1, -1), 4),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(evd_table)
        elements.append(Spacer(1, 0.4 * cm))

    # AI / template narrative
    if narrative:
        elements.append(Paragraph("Investigation Narrative", heading2_style))
        # Split on double newlines to preserve paragraph breaks
        for para in narrative.split("\n\n"):
            para = para.strip()
            if para:
                elements.append(Paragraph(para.replace("\n", "<br/>"), body_style))
                elements.append(Spacer(1, 0.2 * cm))
        elements.append(Spacer(1, 0.2 * cm))

    # Footer note
    elements.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    elements.append(Spacer(1, 0.2 * cm))
    elements.append(Paragraph(
        "<i>This report is confidential and generated by Jackdaw Sentry. "
        "Handle in accordance with your organisation's data-handling policies.</i>",
        body_style,
    ))

    doc.build(elements, onFirstPage=_add_page_number, onLaterPages=_add_page_number)
    return buffer.getvalue()
