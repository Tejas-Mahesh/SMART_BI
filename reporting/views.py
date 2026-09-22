import json
from io import BytesIO

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
    SimpleDocTemplate,
)

from data_management.models import Dataset, DatasetVersion
from data_management.views import read_dataset_version_file

from .models import AutomatedReport, CustomReport
from .report_engine import generate_report
from .custom_report_engine import generate_custom_report


# ============================================================
# COMMON CONSTANTS
# ============================================================

REPORT_TYPES = [
    ("Executive", "Executive"),
    ("Sales", "Sales"),
    ("Customer", "Customer"),
    ("Product", "Product"),
    ("Regional", "Regional"),
    ("Marketing", "Marketing"),
    ("Financial", "Financial"),
    ("Returns", "Returns"),
    ("Operational", "Operational"),
]

VALID_REPORT_TYPES = {
    "Executive",
    "Sales",
    "Customer",
    "Product",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
    "Operational",
}

OUTPUT_FORMATS = [
    ("Dashboard", "Dashboard"),
    ("PDF", "PDF"),
    ("Excel", "Excel"),
]

VALID_OUTPUT_FORMATS = {
    "Dashboard",
    "PDF",
    "Excel",
}


# ============================================================
# APPROVAL CHECK
# ============================================================

def user_is_approved(request):
    """
    Allow reporting only for authenticated and approved users.
    """

    if not request.user.is_authenticated:
        return False

    return (
        getattr(
            request.user,
            "approval_status",
            "",
        )
        == "Approved"
    )


# ============================================================
# DATASET / VERSION HELPERS
# ============================================================

def get_user_datasets(request):
    """
    Return only active datasets belonging to the logged-in user.
    """

    return (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )


def get_selected_dataset(request, datasets):
    """
    Resolve the selected dataset safely from GET/POST.

    If no valid dataset is supplied, the newest dataset is used.
    """

    dataset_id = (
        request.GET.get("dataset")
        or request.POST.get("dataset")
    )

    if dataset_id:
        try:
            return datasets.get(id=dataset_id)

        except (
            Dataset.DoesNotExist,
            ValueError,
            TypeError,
        ):
            return None

    return datasets.first()


def get_dataset_versions(selected_dataset):
    """
    Return versions belonging to the selected dataset.
    """

    if not selected_dataset:
        return DatasetVersion.objects.none()

    return (
        selected_dataset.versions
        .all()
        .order_by(
            "-version_number",
            "-created_at",
        )
    )


def get_selected_version(request, selected_dataset, versions):
    """
    Resolve dataset version.

    Priority:
        1. Explicit version selected by user.
        2. Current version.
        3. Latest version.
    """

    if not selected_dataset:
        return None

    version_id = (
        request.GET.get("version")
        or request.POST.get("version")
    )

    if version_id:
        try:
            return versions.get(id=version_id)

        except (
            DatasetVersion.DoesNotExist,
            ValueError,
            TypeError,
        ):
            pass

    selected_version = (
        versions
        .filter(
            is_current=True
        )
        .first()
    )

    if selected_version:
        return selected_version

    return versions.first()


def get_selected_dataset_and_version(request):
    """
    Common dataset/version resolution used by reporting views.
    """

    datasets = get_user_datasets(request)

    selected_dataset = get_selected_dataset(
        request,
        datasets,
    )

    versions = get_dataset_versions(
        selected_dataset
    )

    selected_version = get_selected_version(
        request,
        selected_dataset,
        versions,
    )

    return (
        datasets,
        selected_dataset,
        versions,
        selected_version,
    )


# ============================================================
# PDF HELPERS
# ============================================================

def pdf_safe(value):
    """
    Convert arbitrary report values into readable PDF text.
    """

    if value is None:
        return ""

    if isinstance(value, bool):
        return "Yes" if value else "No"

    if isinstance(value, (dict, list, tuple)):
        try:
            return json.dumps(
                value,
                ensure_ascii=False,
                default=str,
            )
        except Exception:
            return str(value)

    return str(value)


def pdf_paragraph(value, style):
    """
    Safely convert a value into a ReportLab Paragraph.
    """

    text = pdf_safe(value)

    text = (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    return Paragraph(
        text,
        style,
    )


def build_pdf_styles():
    """
    Build styles used by reporting PDFs.
    """

    styles = getSampleStyleSheet()

    styles.add(
        ParagraphStyle(
            name="ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#17365D"),
            spaceAfter=8,
        )
    )

    styles.add(
        ParagraphStyle(
            name="ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#5B6777"),
            spaceAfter=16,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=colors.HexColor("#17365D"),
            spaceBefore=12,
            spaceAfter=7,
        )
    )

    styles.add(
        ParagraphStyle(
            name="BodyReport",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#252B33"),
            spaceAfter=5,
        )
    )

    styles.add(
        ParagraphStyle(
            name="SmallReport",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7.5,
            leading=10,
            textColor=colors.HexColor("#555F6D"),
        )
    )

    styles.add(
        ParagraphStyle(
            name="KpiValue",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#17365D"),
        )
    )

    return styles


def add_pdf_table(
    story,
    headers,
    rows,
    styles,
    max_columns=8,
):
    """
    Add a readable table to the PDF.

    Long tables are limited to max_columns so the PDF
    remains readable on A4 pages.
    """

    if not headers:
        return

    headers = list(headers)[:max_columns]

    prepared_rows = []

    for row in rows:

        if isinstance(row, dict):

            values = [
                row.get(
                    header,
                    "",
                )
                for header in headers
            ]

        elif isinstance(row, (list, tuple)):

            values = list(row)[:max_columns]

        else:

            values = [row]

        while len(values) < len(headers):
            values.append("")

        prepared_rows.append(
            [
                pdf_paragraph(
                    value,
                    styles["SmallReport"],
                )
                for value in values
            ]
        )

    table_data = [
        [
            pdf_paragraph(
                header,
                styles["SmallReport"],
            )
            for header in headers
        ]
    ]

    table_data.extend(
        prepared_rows
    )

    available_width = 180 * mm

    column_width = (
        available_width / len(headers)
    )

    column_widths = [
        column_width
        for _ in headers
    ]

    table = Table(
        table_data,
        colWidths=column_widths,
        repeatRows=1,
        hAlign="LEFT",
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#17365D"),
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
                    0.35,
                    colors.HexColor("#D7DEE8"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F4F7FA"),
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
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

    story.append(table)
    story.append(
        Spacer(1, 8)
    )


def add_pdf_section(
    story,
    section,
    styles,
):
    """
    Render one generated report section.
    """

    if not isinstance(section, dict):

        story.append(
            pdf_paragraph(
                section,
                styles["BodyReport"],
            )
        )

        return

    title = (
        section.get("title")
        or section.get("name")
        or section.get("heading")
        or "Report Section"
    )

    story.append(
        Paragraph(
            pdf_safe(title),
            styles["SectionHeading"],
        )
    )

    description = (
        section.get("description")
        or section.get("text")
        or ""
    )

    if description:

        story.append(
            pdf_paragraph(
                description,
                styles["BodyReport"],
            )
        )

    rows = (
        section.get("rows")
        or section.get("data")
        or section.get("records")
        or []
    )

    headers = (
        section.get("headers")
        or section.get("columns")
        or []
    )

    if rows:

        if not headers:

            if isinstance(
                rows[0],
                dict,
            ):

                headers = list(
                    rows[0].keys()
                )

            elif isinstance(
                rows[0],
                (list, tuple),
            ):

                headers = [
                    f"Column {index + 1}"
                    for index in range(
                        len(rows[0])
                    )
                ]

        if headers:

            add_pdf_table(
                story=story,
                headers=headers,
                rows=rows,
                styles=styles,
            )

    ignored_keys = {
        "title",
        "name",
        "heading",
        "description",
        "text",
        "rows",
        "data",
        "records",
        "headers",
        "columns",
    }

    for key, value in section.items():

        if key in ignored_keys:
            continue

        if value in (
            None,
            "",
            [],
            {},
        ):
            continue

        story.append(
            Paragraph(
                (
                    f"<b>{pdf_safe(key)}:</b> "
                    f"{pdf_safe(value)}"
                ),
                styles["BodyReport"],
            )
        )


def build_custom_report_pdf(report):
    """
    Create a PDF for a completed CustomReport.
    """

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
        title=report.title,
        author="Smart Business Intelligence",
    )

    styles = build_pdf_styles()

    story = []

    # ========================================================
    # HEADER
    # ========================================================

    story.append(
        Paragraph(
            pdf_safe(report.title),
            styles["ReportTitle"],
        )
    )

    story.append(
        Paragraph(
            (
                f"{pdf_safe(report.report_type)} Report"
                f" &nbsp;|&nbsp; "
                f"Dataset: "
                f"{pdf_safe(report.dataset.name)}"
            ),
            styles["ReportSubtitle"],
        )
    )

    # ========================================================
    # DESCRIPTION
    # ========================================================

    if report.description:

        story.append(
            Paragraph(
                "Description",
                styles["SectionHeading"],
            )
        )

        story.append(
            pdf_paragraph(
                report.description,
                styles["BodyReport"],
            )
        )

    # ========================================================
    # REPORT INFORMATION
    # ========================================================

    story.append(
        Paragraph(
            "Report Information",
            styles["SectionHeading"],
        )
    )

    information_rows = [
        [
            "Report Type",
            pdf_safe(report.report_type),
        ],
        [
            "Dataset",
            pdf_safe(report.dataset.name),
        ],
        [
            "Dataset Version",
            pdf_safe(
                report.dataset_version.version_number
            ),
        ],
        [
            "Version Type",
            pdf_safe(
                report.dataset_version.version_type
            ),
        ],
        [
            "Output Format",
            pdf_safe(report.output_format),
        ],
        [
            "Status",
            pdf_safe(report.status),
        ],
    ]

    add_pdf_table(
        story=story,
        headers=[
            "Property",
            "Value",
        ],
        rows=information_rows,
        styles=styles,
        max_columns=2,
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = report.summary or {}

    if summary:

        story.append(
            Paragraph(
                "Summary",
                styles["SectionHeading"],
            )
        )

        summary_rows = [
            [
                key,
                value,
            ]
            for key, value in summary.items()
        ]

        add_pdf_table(
            story=story,
            headers=[
                "Metric",
                "Value",
            ],
            rows=summary_rows,
            styles=styles,
            max_columns=2,
        )

    # ========================================================
    # KPIs
    # ========================================================

    kpis = report.kpis or []

    if kpis:

        story.append(
            Paragraph(
                "Key Performance Indicators",
                styles["SectionHeading"],
            )
        )

        kpi_rows = []

        for kpi in kpis:

            if isinstance(
                kpi,
                dict,
            ):

                label = (
                    kpi.get("label")
                    or kpi.get("name")
                    or kpi.get("title")
                    or "KPI"
                )

                value = (
                    kpi.get("value")
                    if "value" in kpi
                    else kpi.get(
                        "metric",
                        "",
                    )
                )

                kpi_rows.append(
                    [
                        label,
                        value,
                    ]
                )

            else:

                kpi_rows.append(
                    [
                        "KPI",
                        kpi,
                    ]
                )

        add_pdf_table(
            story=story,
            headers=[
                "KPI",
                "Value",
            ],
            rows=kpi_rows,
            styles=styles,
            max_columns=2,
        )

    # ========================================================
    # SECTIONS
    # ========================================================

    sections = report.sections or []

    if sections:

        story.append(
            PageBreak()
        )

        story.append(
            Paragraph(
                "Detailed Report",
                styles["SectionHeading"],
            )
        )

        for section in sections:

            add_pdf_section(
                story=story,
                section=section,
                styles=styles,
            )

    # ========================================================
    # INSIGHTS
    # ========================================================

    insights = report.insights or []

    if insights:

        story.append(
            Paragraph(
                "Insights",
                styles["SectionHeading"],
            )
        )

        for index, insight in enumerate(
            insights,
            start=1,
        ):

            if isinstance(
                insight,
                dict,
            ):

                title = (
                    insight.get("title")
                    or insight.get("label")
                    or f"Insight {index}"
                )

                text = (
                    insight.get("text")
                    or insight.get("description")
                    or insight.get("message")
                    or insight.get("insight")
                    or ""
                )

                story.append(
                    Paragraph(
                        (
                            f"<b>{index}. "
                            f"{pdf_safe(title)}</b>"
                        ),
                        styles["BodyReport"],
                    )
                )

                if text:

                    story.append(
                        pdf_paragraph(
                            text,
                            styles["BodyReport"],
                        )
                    )

            else:

                story.append(
                    Paragraph(
                        (
                            f"<b>{index}.</b> "
                            f"{pdf_safe(insight)}"
                        ),
                        styles["BodyReport"],
                    )
                )

    # ========================================================
    # METADATA
    # ========================================================

    metadata = report.metadata or {}

    if metadata:

        story.append(
            Paragraph(
                "Report Metadata",
                styles["SectionHeading"],
            )
        )

        metadata_rows = [
            [
                key,
                value,
            ]
            for key, value in metadata.items()
        ]

        add_pdf_table(
            story=story,
            headers=[
                "Property",
                "Value",
            ],
            rows=metadata_rows,
            styles=styles,
            max_columns=2,
        )

    # ========================================================
    # FOOTER
    # ========================================================

    generated_text = ""

    if report.generated_at:

        generated_text = (
            report.generated_at.strftime(
                "%d %B %Y, %I:%M %p"
            )
        )

    story.append(
        Spacer(1, 12)
    )

    story.append(
        Paragraph(
            (
                "Generated by Smart Business Intelligence"
                + (
                    f" on {generated_text}"
                    if generated_text
                    else ""
                )
            ),
            styles["SmallReport"],
        )
    )

    document.build(story)

    buffer.seek(0)

    return buffer


# ============================================================
# AUTOMATED REPORTS
# ============================================================

@login_required
def automated_reports(request):
    """
    Automated Reports page.

    Flow:

        User
          ↓
        Dataset
          ↓
        DatasetVersion
          ↓
        Report Engine
          ↓
        AutomatedReport
    """

    # ========================================================
    # APPROVAL
    # ========================================================

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            },
        )

    # ========================================================
    # DATASET / VERSION
    # ========================================================

    (
        datasets,
        selected_dataset,
        versions,
        selected_version,
    ) = get_selected_dataset_and_version(
        request
    )

    # ========================================================
    # GENERATE REPORT
    # ========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        if action == "generate":

            if not selected_dataset:

                messages.error(
                    request,
                    "Please select a dataset.",
                )

                return redirect(
                    "reporting:automated_reports"
                )

            if not selected_version:

                messages.error(
                    request,
                    (
                        "The selected dataset has no "
                        "available version."
                    ),
                )

                return redirect(
                    "reporting:automated_reports"
                )

            report_type = (
                request.POST.get(
                    "report_type",
                    "Executive",
                )
                .strip()
            )

            title = (
                request.POST.get(
                    "title",
                    "",
                )
                .strip()
            )

            description = (
                request.POST.get(
                    "description",
                    "",
                )
                .strip()
            )

            if report_type not in VALID_REPORT_TYPES:

                messages.error(
                    request,
                    "Invalid report type selected.",
                )

                return redirect(
                    "reporting:automated_reports"
                )

            if not title:

                title = (
                    f"{report_type} Report - "
                    f"{selected_dataset.name}"
                )

            # =================================================
            # CREATE REPORT
            # =================================================

            report = AutomatedReport.objects.create(
                dataset=selected_dataset,
                dataset_version=selected_version,
                created_by=request.user,
                title=title,
                description=description,
                report_type=report_type,
                status="Generating",
                output_format="Dashboard",
            )

            try:

                # ---------------------------------------------
                # READ CLEANED / VERSIONED DATA
                # ---------------------------------------------

                dataframe = (
                    read_dataset_version_file(
                        selected_version
                    )
                )

                # ---------------------------------------------
                # GENERATE REPORT
                # ---------------------------------------------

                result = generate_report(
                    dataframe=dataframe,
                    report_type=report_type,
                )

                # ---------------------------------------------
                # SAVE GENERATED CONTENT
                # ---------------------------------------------

                report.summary = result.get(
                    "summary",
                    {},
                )

                report.kpis = result.get(
                    "kpis",
                    [],
                )

                report.sections = result.get(
                    "sections",
                    [],
                )

                report.charts = result.get(
                    "charts",
                    [],
                )

                report.insights = result.get(
                    "insights",
                    [],
                )

                report.metadata = result.get(
                    "metadata",
                    {},
                )

                report.status = "Completed"
                report.error_message = ""
                report.generated_at = timezone.now()

                report.save()

                messages.success(
                    request,
                    "Automated report generated successfully.",
                )

                return redirect(
                    "reporting:automated_reports"
                )

            except Exception as exc:

                report.status = "Failed"
                report.error_message = str(exc)

                report.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "updated_at",
                    ]
                )

                messages.error(
                    request,
                    (
                        "Unable to generate the report. "
                        f"{exc}"
                    ),
                )

                return redirect(
                    "reporting:automated_reports"
                )

    # ========================================================
    # REPORT HISTORY
    # ========================================================

    reports = (
        AutomatedReport.objects
        .filter(
            created_by=request.user,
            dataset__owner=request.user,
        )
        .select_related(
            "dataset",
            "dataset_version",
            "created_by",
        )
        .order_by("-created_at")
    )

    # ========================================================
    # LATEST REPORT
    # ========================================================

    selected_report = reports.first()

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {
        "total": reports.count(),

        "completed": reports.filter(
            status="Completed"
        ).count(),

        "generating": reports.filter(
            status="Generating"
        ).count(),

        "failed": reports.filter(
            status="Failed"
        ).count(),
    }

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "reports": reports,
        "selected_report": selected_report,
        "report_types": REPORT_TYPES,
        "summary": summary,
    }

    return render(
        request,
        "reporting/automated_reports.html",
        context,
    )


# ============================================================
# CUSTOM REPORTS
# ============================================================

@login_required
def custom_reports(request):
    """
    Custom report builder.

    Uses the cleaned/current DatasetVersion as the primary
    source of reporting data.
    """

    # ========================================================
    # APPROVAL
    # ========================================================

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved by the "
                    "administrator yet."
                )
            },
        )

    # ========================================================
    # DATASET / VERSION
    # ========================================================

    (
        datasets,
        selected_dataset,
        versions,
        selected_version,
    ) = get_selected_dataset_and_version(
        request
    )

    # ========================================================
    # DATASET COLUMN INFORMATION
    # ========================================================

    columns = []
    numeric_columns = []
    categorical_columns = []
    date_columns = []

    dataframe = None

    if selected_version:

        try:

            dataframe = (
                read_dataset_version_file(
                    selected_version
                )
            )

            columns = [
                str(column)
                for column in dataframe.columns
            ]

            numeric_columns = [
                str(column)
                for column
                in dataframe.select_dtypes(
                    include="number"
                ).columns
            ]

            date_columns = [
                str(column)
                for column
                in dataframe.select_dtypes(
                    include=[
                        "datetime",
                        "datetimetz",
                    ]
                ).columns
            ]

            numeric_set = set(
                numeric_columns
            )

            date_set = set(
                date_columns
            )

            categorical_columns = [
                column
                for column in columns
                if column not in numeric_set
                and column not in date_set
            ]

        except Exception as exc:

            messages.error(
                request,
                (
                    "Unable to read the selected dataset "
                    f"version. {exc}"
                ),
            )

    # ========================================================
    # POST ACTIONS
    # ========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        # ====================================================
        # GENERATE CUSTOM REPORT
        # ====================================================

        if action == "generate":

            if not selected_dataset:

                messages.error(
                    request,
                    "Please select a dataset.",
                )

                return redirect(
                    "reporting:custom_reports"
                )

            if not selected_version:

                messages.error(
                    request,
                    (
                        "The selected dataset has no "
                        "available version."
                    ),
                )

                return redirect(
                    "reporting:custom_reports"
                )

            if dataframe is None:

                messages.error(
                    request,
                    (
                        "The selected dataset version "
                        "could not be read."
                    ),
                )

                return redirect(
                    "reporting:custom_reports"
                )

            # ------------------------------------------------
            # FORM VALUES
            # ------------------------------------------------

            title = (
                request.POST.get(
                    "title",
                    "",
                )
                .strip()
            )

            description = (
                request.POST.get(
                    "description",
                    "",
                )
                .strip()
            )

            report_type = (
                request.POST.get(
                    "report_type",
                    "Executive",
                )
                .strip()
            )

            output_format = (
                request.POST.get(
                    "output_format",
                    "Dashboard",
                )
                .strip()
            )

            selected_columns = (
                request.POST.getlist(
                    "selected_columns"
                )
            )

            selected_metrics = (
                request.POST.getlist(
                    "selected_metrics"
                )
            )

            selected_dimensions = (
                request.POST.getlist(
                    "selected_dimensions"
                )
            )

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            if report_type not in VALID_REPORT_TYPES:

                messages.error(
                    request,
                    "Invalid report type selected.",
                )

                return redirect(
                    "reporting:custom_reports"
                )

            if output_format not in VALID_OUTPUT_FORMATS:

                messages.error(
                    request,
                    "Invalid output format selected.",
                )

                return redirect(
                    "reporting:custom_reports"
                )

            # ------------------------------------------------
            # KEEP ONLY REAL DATAFRAME COLUMNS
            # ------------------------------------------------

            selected_columns = [
                column
                for column in selected_columns
                if column in columns
            ]

            selected_metrics = [
                column
                for column in selected_metrics
                if column in numeric_columns
            ]

            selected_dimensions = [
                column
                for column in selected_dimensions
                if column in columns
            ]

            if not title:

                title = (
                    f"Custom {report_type} Report - "
                    f"{selected_dataset.name}"
                )

            # ------------------------------------------------
            # CREATE REPORT
            # ------------------------------------------------

            report = CustomReport.objects.create(
                dataset=selected_dataset,
                dataset_version=selected_version,
                created_by=request.user,
                title=title,
                description=description,
                report_type=report_type,
                status="Generating",
                output_format=output_format,
                selected_columns=selected_columns,
                selected_metrics=selected_metrics,
                selected_dimensions=selected_dimensions,
                filters=[],
                sort_configuration={},
                chart_configuration=[],
            )

            # =================================================
            # GENERATE
            # =================================================

            try:

                result = generate_custom_report(
                    dataframe=dataframe,
                    selected_columns=selected_columns,
                    selected_metrics=selected_metrics,
                    selected_dimensions=selected_dimensions,
                    filters=report.filters,
                    sort_configuration=(
                        report.sort_configuration
                    ),
                    chart_configuration=(
                        report.chart_configuration
                    ),
                )

                # ------------------------------------------------
                # SAVE GENERATED RESULT
                # ------------------------------------------------

                report.summary = result.get(
                    "summary",
                    {},
                )

                report.kpis = result.get(
                    "kpis",
                    [],
                )

                report.sections = result.get(
                    "sections",
                    [],
                )

                report.charts = result.get(
                    "charts",
                    [],
                )

                report.insights = result.get(
                    "insights",
                    [],
                )

                report.metadata = result.get(
                    "metadata",
                    {},
                )

                report.status = "Completed"
                report.error_message = ""
                report.generated_at = timezone.now()

                report.save()

                messages.success(
                    request,
                    (
                        "Custom report generated "
                        "successfully."
                    ),
                )

                return redirect(
                    "reporting:custom_reports"
                )

            # =================================================
            # GENERATION ERROR
            # =================================================

            except Exception as exc:

                report.status = "Failed"
                report.error_message = str(exc)

                report.save(
                    update_fields=[
                        "status",
                        "error_message",
                        "updated_at",
                    ]
                )

                messages.error(
                    request,
                    (
                        "Unable to generate the custom "
                        f"report. {exc}"
                    ),
                )

                return redirect(
                    "reporting:custom_reports"
                )

    # ========================================================
    # REPORT HISTORY
    # ========================================================

    reports = (
        CustomReport.objects
        .filter(
            created_by=request.user,
            dataset__owner=request.user,
        )
        .select_related(
            "dataset",
            "dataset_version",
            "created_by",
        )
        .order_by("-created_at")
    )

    # ========================================================
    # MOST RECENT COMPLETED REPORT
    # ========================================================

    selected_report = (
        reports
        .filter(
            status="Completed"
        )
        .first()
    )

    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {
        "total": reports.count(),

        "completed": reports.filter(
            status="Completed"
        ).count(),

        "generating": reports.filter(
            status="Generating"
        ).count(),

        "draft": reports.filter(
            status="Draft"
        ).count(),

        "failed": reports.filter(
            status="Failed"
        ).count(),
    }

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "columns": columns,
        "numeric_columns": numeric_columns,
        "categorical_columns": categorical_columns,
        "date_columns": date_columns,
        "reports": reports,
        "selected_report": selected_report,
        "summary": summary,
        "report_types": REPORT_TYPES,
        "output_formats": OUTPUT_FORMATS,
    }

    return render(
        request,
        "reporting/custom_reports.html",
        context,
    )


# ============================================================
# CUSTOM REPORT PDF EXPORT
# ============================================================

@login_required
def custom_report_pdf(request, report_id):
    """
    Download a completed CustomReport as a PDF.

    Security:
    - User must be authenticated.
    - User must be approved.
    - Report must belong to the logged-in user.
    - Dataset must belong to the logged-in user.
    - Only completed reports can be exported.
    """

    # ========================================================
    # APPROVAL
    # ========================================================

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            },
        )

    # ========================================================
    # GET REPORT
    # ========================================================

    report = get_object_or_404(
        CustomReport.objects.select_related(
            "dataset",
            "dataset_version",
            "created_by",
        ),
        id=report_id,
        created_by=request.user,
        dataset__owner=request.user,
    )

    # ========================================================
    # REPORT STATUS
    # ========================================================

    if report.status != "Completed":

        messages.error(
            request,
            (
                "This report is not completed yet and "
                "cannot be exported as PDF."
            ),
        )

        return redirect(
            "reporting:custom_reports"
        )

    # ========================================================
    # GENERATE PDF
    # ========================================================

    try:

        pdf_buffer = build_custom_report_pdf(
            report
        )

    except Exception as exc:

        messages.error(
            request,
            (
                "Unable to create the PDF. "
                f"{exc}"
            ),
        )

        return redirect(
            "reporting:custom_reports"
        )

    # ========================================================
    # FILE NAME
    # ========================================================

    safe_title = "".join(
        character
        if (
            character.isalnum()
            or character in (
                " ",
                "-",
                "_",
            )
        )
        else "_"
        for character in report.title
    ).strip()

    safe_title = (
        safe_title
        or f"custom_report_{report.id}"
    )

    filename = f"{safe_title}.pdf"

    # ========================================================
    # HTTP RESPONSE
    # ========================================================

    pdf_content = pdf_buffer.getvalue()

    response = HttpResponse(
        pdf_content,
        content_type="application/pdf",
    )

    response["Content-Disposition"] = (
        f'attachment; filename="{filename}"'
    )

    response["Content-Length"] = str(
        len(pdf_content)
    )

    return response