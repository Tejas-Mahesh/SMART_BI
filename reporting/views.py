from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

from data_management.models import Dataset
from .models import Report
from .services.report_generator import generate_report_files
from django.http import FileResponse
@login_required
def dashboard(request):
    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    reports = (
        Report.objects
        .filter(owner=request.user)
        .select_related("dataset")
        .order_by("-created_at")
    )

    selected_dataset = None

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    if selected_dataset is None:
        selected_dataset = datasets.first()

    context = {
        "datasets": datasets,
        "reports": reports[:10],
        "selected_dataset": selected_dataset,

        "total_reports": reports.count(),

        "generated_reports": reports.filter(
            status="Generated"
        ).count(),

        "processing_reports": reports.filter(
            status="Processing"
        ).count(),

        "failed_reports": reports.filter(
            status="Failed"
        ).count(),
    }

    return render(
        request,
        "reporting/dashboard.html",
        context,
    )


@login_required
def generate_report(request):

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if request.method != "POST":
        return redirect(
            "reporting:dashboard"
        )

    dataset_id = request.POST.get(
        "dataset"
    )

    report_type = request.POST.get(
        "report_type",
        "Business Summary",
    )

    output_format = request.POST.get(
        "output_format",
        "PDF",
    )

    title = request.POST.get(
        "title",
        "",
    ).strip()

    description = request.POST.get(
        "description",
        "",
    ).strip()

    dataset = (
        datasets
        .filter(id=dataset_id)
        .first()
    )

    if dataset is None:
        messages.error(
            request,
            "Please select a valid dataset.",
        )

        return redirect(
            "reporting:dashboard"
        )

    if not title:
        title = (
            f"{report_type} - "
            f"{dataset.name}"
        )

    allowed_report_types = {
        "Business Summary",
        "Sales Report",
        "Customer Report",
        "Product Report",
        "Regional Report",
        "Financial Report",
        "Marketing Report",
        "Decision Report",
        "Executive Report",
    }

    allowed_formats = {
        "PDF",
        "Excel",
        "Both",
    }

    if report_type not in allowed_report_types:
        report_type = "Business Summary"

    if output_format not in allowed_formats:
        output_format = "PDF"

    report = Report.objects.create(
        owner=request.user,
        dataset=dataset,
        title=title,
        report_type=report_type,
        output_format=output_format,
        status="Processing",
        description=description,
    )

    messages.success(
        request,
        (
            f'Report "{report.title}" '
            "has been created and is ready "
            "for report processing."
        ),
    )

    return redirect(
        "reporting:dashboard"
    )

@login_required
def generate_report(request):

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if request.method != "POST":
        return redirect("reporting:dashboard")

    dataset_id = request.POST.get("dataset")

    report_type = request.POST.get(
        "report_type",
        "Business Summary",
    )

    output_format = request.POST.get(
        "output_format",
        "PDF",
    )

    title = request.POST.get(
        "title",
        "",
    ).strip()

    description = request.POST.get(
        "description",
        "",
    ).strip()

    dataset = (
        datasets
        .filter(id=dataset_id)
        .first()
    )

    if dataset is None:
        messages.error(
            request,
            "Please select a valid dataset.",
        )

        return redirect(
            "reporting:dashboard"
        )

    allowed_report_types = {
        "Business Summary",
        "Sales Report",
        "Customer Report",
        "Product Report",
        "Regional Report",
        "Financial Report",
        "Marketing Report",
        "Decision Report",
        "Executive Report",
    }

    allowed_formats = {
        "PDF",
        "Excel",
        "Both",
    }

    if report_type not in allowed_report_types:
        report_type = "Business Summary"

    if output_format not in allowed_formats:
        output_format = "PDF"

    if not title:
        title = (
            f"{report_type} - "
            f"{dataset.name}"
        )

    # ---------------------------------------------------------
    # CREATE REPORT RECORD
    # ---------------------------------------------------------

    report = Report.objects.create(
        owner=request.user,
        dataset=dataset,
        title=title,
        report_type=report_type,
        output_format=output_format,
        status="Processing",
        description=description,
    )

    # ---------------------------------------------------------
    # GENERATE ACTUAL FILES
    # ---------------------------------------------------------

    try:

        generated_files = generate_report_files(
            report
        )

        summary = generated_files.get(
            "summary",
            {},
        )

        # -----------------------------------------------------
        # SAVE PDF
        # -----------------------------------------------------

        pdf_path = generated_files.get(
            "pdf"
        )

        if pdf_path:

            with open(
                pdf_path,
                "rb",
            ) as pdf_file:

                report.pdf_file.save(
                    pdf_path.name,
                    pdf_file,
                    save=False,
                )

        # -----------------------------------------------------
        # SAVE EXCEL
        # -----------------------------------------------------

        excel_path = generated_files.get(
            "excel"
        )

        if excel_path:

            with open(
                excel_path,
                "rb",
            ) as excel_file:

                report.excel_file.save(
                    excel_path.name,
                    excel_file,
                    save=False,
                )

        # -----------------------------------------------------
        # UPDATE ANALYTICS SUMMARY
        # -----------------------------------------------------

        report.total_recommendations = 0

        report.critical_recommendations = 0

        report.high_recommendations = 0

        report.average_decision_score = 0

        report.learning_score = 0

        report.feedback_learning_score = 0

        report.report_data = {
    "rows": int(summary.get("rows", 0)),
    "columns": int(summary.get("columns", 0)),
    "missing": int(summary.get("missing", 0)),
    "duplicates": int(summary.get("duplicates", 0)),
    "quality": float(summary.get("quality", 0)),
    "revenue": float(summary.get("revenue", 0)),
    "quantity": float(summary.get("quantity", 0)),
    "returns": float(summary.get("returns", 0)),
    "average_value": float(summary.get("average_value", 0)),
}

        report.status = "Generated"

        report.save()

        messages.success(
            request,
            (
                f'Report "{report.title}" '
                "generated successfully."
            ),
        )

    except Exception as exc:

        report.status = "Failed"

        report.report_data = {
            "error": str(exc),
        }

        report.save()

        messages.error(
            request,
            (
                "Report generation failed: "
                f"{exc}"
            ),
        )

    return redirect(
        "reporting:dashboard"
    )

@login_required
def download_pdf(request, report_id):

    report = (
        Report.objects
        .filter(
            id=report_id,
            owner=request.user,
            status="Generated",
        )
        .first()
    )

    if report is None:
        messages.error(
            request,
            "Report not found.",
        )

        return redirect(
            "reporting:dashboard"
        )

    if not report.pdf_file:
        messages.error(
            request,
            "PDF file is not available for this report.",
        )

        return redirect(
            "reporting:dashboard"
        )

    response = FileResponse(
        report.pdf_file.open("rb"),
        as_attachment=True,
        filename=f"{report.title}.pdf",
        content_type="application/pdf",
    )

    return response


@login_required
def download_excel(request, report_id):

    report = (
        Report.objects
        .filter(
            id=report_id,
            owner=request.user,
            status="Generated",
        )
        .first()
    )

    if report is None:
        messages.error(
            request,
            "Report not found.",
        )

        return redirect(
            "reporting:dashboard"
        )

    if not report.excel_file:
        messages.error(
            request,
            "Excel file is not available for this report.",
        )

        return redirect(
            "reporting:dashboard"
        )

    response = FileResponse(
        report.excel_file.open("rb"),
        as_attachment=True,
        filename=f"{report.title}.xlsx",
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )

    return response