"""Plain, printer-friendly PDF report generation with ReportLab."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from utils.categories import TYPE_LABELS
from utils.dates import format_date
from utils.money import format_money
from utils.stats import summarize

INK = colors.black
BORDER = colors.HexColor("#9ca3af")
HEADER_BACKGROUND = colors.HexColor("#e5e7eb")


def _text(value):
    text = "" if value is None else str(value)
    text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\t", "    ")
    text = "".join(ch for ch in text if ch == "\n" or ord(ch) >= 32)
    return escape(text).replace("\n", "<br/>")


def _period_label(filters):
    start = filters.get("start_date") or ""
    end = filters.get("end_date") or ""
    if start and end:
        return f"{start} to {end}"
    if start:
        return f"From {start}"
    if end:
        return f"Up to {end}"
    return "All recorded transactions"


def _filter_label(filters):
    parts = [
        f"Type: {TYPE_LABELS.get(filters.get('type', 'all'), 'All')}"
        if filters.get("type", "all") != "all"
        else "Type: All",
        f"Category: {filters.get('category', 'all')}"
        if filters.get("category", "all") != "all"
        else "Category: All",
    ]
    if filters.get("q"):
        parts.append(f"Keyword: {filters['q']}")
    return " | ".join(parts)


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(INK)
    canvas.setFont("Helvetica", 8)
    page_width, _ = landscape(A4)
    canvas.drawRightString(page_width - 14 * mm, 8 * mm, f"Page {doc.page}")
    canvas.restoreState()


def build_report_pdf(documents, filters, generated_on):
    """Return a BytesIO containing the PDF report."""
    buffer = BytesIO()
    page_size = landscape(A4)

    document = SimpleDocTemplate(
        buffer,
        pagesize=page_size,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
        title="Expense tracker",
        author="Expense tracker",
        subject="Expense report",
    )

    title_style = ParagraphStyle(
        "ReportTitle",
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=INK,
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=INK,
    )
    summary_style = ParagraphStyle(
        "ReportSummary",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13,
        textColor=INK,
    )
    header_style = ParagraphStyle(
        "TableHeader",
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=10,
        textColor=INK,
    )
    header_right = ParagraphStyle(
        "TableHeaderRight",
        parent=header_style,
        alignment=2,
    )
    body_style = ParagraphStyle(
        "TableBody",
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.5,
        textColor=INK,
    )
    body_right = ParagraphStyle("TableBodyRight", parent=body_style, alignment=2)
    body_center = ParagraphStyle("TableBodyCenter", parent=body_style, alignment=1)

    totals = summarize(documents)

    story = [
        Paragraph("Expense tracker", title_style),
        Paragraph(f"Report period: {_text(_period_label(filters))}", meta_style),
        Paragraph(f"Filters: {_text(_filter_label(filters))}", meta_style),
        Paragraph(f"Generated on: {_text(generated_on)}", meta_style),
        Spacer(1, 8),
        Paragraph(
            f"Total credits: {format_money(totals['credits'])}", summary_style
        ),
        Paragraph(f"Total debits: {format_money(totals['debits'])}", summary_style),
        Paragraph(f"Net balance: {format_money(totals['net'])}", summary_style),
        Paragraph(f"Transactions: {totals['count']}", summary_style),
        Spacer(1, 12),
    ]

    data = [
        [
            Paragraph("S.No.", header_style),
            Paragraph("Date", header_style),
            Paragraph("Type (Credit/Debit)", header_style),
            Paragraph("Title", header_style),
            Paragraph("Description", header_style),
            Paragraph("Amount", header_right),
        ]
    ]

    for index, doc in enumerate(documents, start=1):
        data.append(
            [
                Paragraph(str(index), body_center),
                Paragraph(_text(format_date(doc.get("date"))), body_style),
                Paragraph(
                    _text(TYPE_LABELS.get(doc.get("type"), doc.get("type", ""))),
                    body_style,
                ),
                Paragraph(_text(doc.get("title", "")), body_style),
                Paragraph(_text(doc.get("description", "") or "-"), body_style),
                Paragraph(format_money(doc.get("amount", 0)), body_right),
            ]
        )

    table = Table(
        data,
        colWidths=[13 * mm, 22 * mm, 36 * mm, 57 * mm, 106 * mm, 35 * mm],
        repeatRows=1,
        hAlign="LEFT",
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HEADER_BACKGROUND),
                ("TEXTCOLOR", (0, 0), (-1, -1), INK),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )

    story.append(table)

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    buffer.seek(0)
    return buffer
