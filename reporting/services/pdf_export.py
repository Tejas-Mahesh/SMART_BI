from io import BytesIO

from django.core.files.base import ContentFile
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)

from ..models import ReportExport


# ============================================================
# HELPERS
# ============================================================

def safe_value(value):
    """
    Convert values into PDF-safe display text.
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, float):
        return f"{value:,.2f}"

    if isinstance(value, int):
        return f"{value:,}"

    if isinstance(value, (dict, list)):
        return str(value)

    return str(value)


def create_styles():
    """
    Create PDF styles used throughout the report.
    """

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=10,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.grey,
            spaceAfter=18,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionTitle",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            spaceBefore=12,
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodySmall",
            parent=styles["BodyText"],
            fontSize=9,
            leading=13,
        )
    )

    styles.add(
        ParagraphStyle(
            name="TableText",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
        )
    )

    return styles


# ============================================================
# TABLE BUILDER
# ============================================================

def build_table(data, styles):
    """
    Convert a list of rows into a ReportLab table.
    """

    if not data:
        return None

    table_data = []

    for row in data:

        if isinstance(row, dict):

            table_data.append(
                [
                    Paragraph(
                        safe_value(key),
                        styles["TableText"],
                    )
                    for key in row.keys()
                ]
            )

            break

    if isinstance(data[0], dict):

        headers = list(data[0].keys())

        table_data = [
            [
                Paragraph(
                    safe_value(header),
                    styles["TableText"],
                )
                for header in headers
            ]
        ]

        for row in data:

            table_data.append(
                [
                    Paragraph(
                        safe_value(row.get(header)),
                        styles["TableText"],
                    )
                    for header in headers
                ]
            )

    elif isinstance(data[0], (list, tuple)):

        table_data = [
            [
                Paragraph(
                    safe_value(value),
                    styles["TableText"],
                )
                for value in row
            ]
            for row in data
        ]

    else:
        return None

    if not table_data:
        return None

    column_count = len(table_data[0])

    available_width = 170 * mm

    column_widths = [
        available_width / column_count
        for _ in range(column_count)
    ]

    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#1f2937"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold",
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#d1d5db"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f9fafb"),
                    ],
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


# ============================================================
# PDF GENERATION
# ============================================================

def generate_pdf_export(report):
    """
    Generate a PDF export for a completed Report.

    Returns:
        ReportExport instance
    """

    export = ReportExport.objects.create(
        report=report,
        export_type="PDF",
        status="Generating",
    )

    try:

        buffer = BytesIO()

        document = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=report.name,
            author=str(report.owner),
        )

        styles = create_styles()

        story = []

        # ----------------------------------------------------
        # TITLE
        # ----------------------------------------------------

        story.append(
            Paragraph(
                safe_value(report.name),
                styles["ReportTitle"],
            )
        )

        story.append(
            Paragraph(
                (
                    f"Dataset: {safe_value(report.dataset.name)}"
                    f" &nbsp;|&nbsp; "
                    f"Version: "
                    f"{safe_value(report.dataset_version.version_number)}"
                ),
                styles["ReportSubtitle"],
            )
        )

        # ----------------------------------------------------
        # DESCRIPTION
        # ----------------------------------------------------

        if report.description:

            story.append(
                Paragraph(
                    "Report Description",
                    styles["SectionTitle"],
                )
            )

            story.append(
                Paragraph(
                    safe_value(report.description),
                    styles["BodySmall"],
                )
            )

            story.append(
                Spacer(1, 8)
            )

        # ----------------------------------------------------
        # REPORT INFORMATION
        # ----------------------------------------------------

        story.append(
            Paragraph(
                "Report Information",
                styles["SectionTitle"],
            )
        )

        information = [
            [
                "Report Type",
                safe_value(report.get_report_type_display()),
            ],
            [
                "Status",
                safe_value(report.get_status_display()),
            ],
            [
                "Dataset",
                safe_value(report.dataset.name),
            ],
            [
                "Dataset Version",
                safe_value(
                    report.dataset_version.version_number
                ),
            ],
            [
                "Created",
                report.created_at.strftime(
                    "%d %b %Y, %H:%M"
                ),
            ],
        ]

        information_table = Table(
            information,
            colWidths=[
                55 * mm,
                115 * mm,
            ],
        )

        information_table.setStyle(
            TableStyle(
                [
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.5,
                        colors.HexColor("#d1d5db"),
                    ),
                    (
                        "BACKGROUND",
                        (0, 0),
                        (0, -1),
                        colors.HexColor("#f3f4f6"),
                    ),
                    (
                        "FONTNAME",
                        (0, 0),
                        (0, -1),
                        "Helvetica-Bold",
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "PADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(information_table)

        # ----------------------------------------------------
        # GENERATED DATA
        # ----------------------------------------------------

        generated_data = report.generated_data or {}

        story.append(
            Spacer(1, 12)
        )

        story.append(
            Paragraph(
                "Report Results",
                styles["SectionTitle"],
            )
        )

        if not generated_data:

            story.append(
                Paragraph(
                    "No generated report data is available.",
                    styles["BodySmall"],
                )
            )

        else:

            for section_name, section_data in generated_data.items():

                story.append(
                    Paragraph(
                        safe_value(section_name).replace(
                            "_",
                            " ",
                        ).title(),
                        styles["SectionTitle"],
                    )
                )

                # --------------------------------------------
                # Dictionary
                # --------------------------------------------

                if isinstance(section_data, dict):

                    rows = []

                    for key, value in section_data.items():

                        if isinstance(value, (dict, list)):
                            value = safe_value(value)

                        rows.append(
                            [
                                safe_value(key).replace(
                                    "_",
                                    " ",
                                ).title(),
                                safe_value(value),
                            ]
                        )

                    if rows:

                        table = Table(
                            rows,
                            colWidths=[
                                65 * mm,
                                105 * mm,
                            ],
                        )

                        table.setStyle(
                            TableStyle(
                                [
                                    (
                                        "GRID",
                                        (0, 0),
                                        (-1, -1),
                                        0.5,
                                        colors.HexColor(
                                            "#d1d5db"
                                        ),
                                    ),
                                    (
                                        "BACKGROUND",
                                        (0, 0),
                                        (0, -1),
                                        colors.HexColor(
                                            "#f9fafb"
                                        ),
                                    ),
                                    (
                                        "FONTNAME",
                                        (0, 0),
                                        (0, -1),
                                        "Helvetica-Bold",
                                    ),
                                    (
                                        "VALIGN",
                                        (0, 0),
                                        (-1, -1),
                                        "TOP",
                                    ),
                                    (
                                        "PADDING",
                                        (0, 0),
                                        (-1, -1),
                                        5,
                                    ),
                                ]
                            )
                        )

                        story.append(table)

                # --------------------------------------------
                # List
                # --------------------------------------------

                elif isinstance(section_data, list):

                    table = build_table(
                        section_data,
                        styles,
                    )

                    if table:

                        story.append(table)

                    else:

                        for item in section_data:

                            story.append(
                                Paragraph(
                                    safe_value(item),
                                    styles["BodySmall"],
                                )
                            )

                            story.append(
                                Spacer(1, 4)
                            )

                # --------------------------------------------
                # Scalar
                # --------------------------------------------

                else:

                    story.append(
                        Paragraph(
                            safe_value(section_data),
                            styles["BodySmall"],
                        )
                    )

                story.append(
                    Spacer(1, 8)
                )

        # ----------------------------------------------------
        # FOOTER
        # ----------------------------------------------------

        def draw_footer(canvas, doc):

            canvas.saveState()

            canvas.setFont(
                "Helvetica",
                7,
            )

            canvas.setFillColor(
                colors.grey
            )

            canvas.drawString(
                20 * mm,
                10 * mm,
                "Smart Business Decision Intelligence Management System",
            )

            canvas.drawRightString(
                190 * mm,
                10 * mm,
                f"Page {doc.page}",
            )

            canvas.restoreState()

        document.build(
            story,
            onFirstPage=draw_footer,
            onLaterPages=draw_footer,
        )

        pdf_content = buffer.getvalue()

        buffer.close()

        filename = (
            f"{report.name.replace(' ', '_')}_"
            f"{report.id}.pdf"
        )

        export.file.save(
            filename,
            ContentFile(pdf_content),
            save=False,
        )

        export.status = "Completed"
        export.completed_at = timezone.now()
        export.error_message = ""
        export.save()

        return export

    except Exception as exc:

        export.status = "Failed"
        export.error_message = str(exc)
        export.save()

        raise