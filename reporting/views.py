from django.contrib.auth.decorators import login_required

from data_management.models import Dataset, DatasetVersion

from .forms import (
    AutomatedReportForm,
    CustomReportForm,
)
from .models import Report, CustomReport

from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.db.models import Q
from .models import (
    Report,
    CustomReport,
    ReportExport,
)
from django.http import HttpResponse
from django.core.files.base import ContentFile
from django.utils import timezone

from .models import (
    Report,
    CustomReport,
    ReportExport,
)
# ============================================================
# APPROVAL CHECK
# ============================================================

def user_is_approved(request):
    """
    Reporting is available only to authenticated users
    whose account has been approved by the administrator.
    """

    return (
        request.user.is_authenticated
        and getattr(
            request.user,
            "approval_status",
            None,
        ) == "Approved"
    )


# ============================================================
# COMMON DATASET HELPERS
# ============================================================

def get_user_datasets(user):
    """
    Return only active datasets belonging to the current user.
    """

    return (
        Dataset.objects
        .filter(
            owner=user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )


def get_selected_dataset(request, datasets):
    """
    Return the requested dataset if it belongs to the user.
    Otherwise return the first available dataset.
    """

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

        if dataset:
            return dataset

    return datasets.first()


def get_selected_version(request, dataset):
    """
    Return the requested version belonging to the selected dataset.

    If no version is explicitly selected:
        1. current version
        2. latest version
    """

    if dataset is None:
        return None

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    version_id = request.GET.get("version")

    if version_id:
        version = (
            versions
            .filter(id=version_id)
            .first()
        )

        if version:
            return version

    current_version = (
        versions
        .filter(is_current=True)
        .first()
    )

    if current_version:
        return current_version

    return versions.first()


def reporting_context(request):
    """
    Build the common Reporting dataset/version context.
    """

    datasets = get_user_datasets(
        request.user
    )

    selected_dataset = get_selected_dataset(
        request,
        datasets,
    )

    selected_version = get_selected_version(
        request,
        selected_dataset,
    )

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        if selected_dataset
        else DatasetVersion.objects.none()
    )

    return {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
    }


# ============================================================
# REPORTING DASHBOARD
# ============================================================

@login_required
def reporting_dashboard(request):
    """
    Main Reporting dashboard.

    Report generation will be added after the foundation
    is verified.
    """

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

    context = reporting_context(request)

    context.update(
        {
            "recent_reports": (
                Report.objects
                .filter(
                    owner=request.user,
                )
                .select_related(
                    "dataset",
                    "dataset_version",
                )
                .order_by(
                    "-created_at",
                )[:5]
            ),
            "recent_custom_reports": (
                CustomReport.objects
                .filter(
                    owner=request.user,
                    is_active=True,
                )
                .select_related(
                    "dataset",
                    "dataset_version",
                )
                .order_by(
                    "-updated_at",
                )[:5]
            ),
        }
    )

    return render(
        request,
        "reporting/dashboard.html",
        context,
    )


# ============================================================
# AUTOMATED REPORTS
# ============================================================

@login_required
def automated_reports(request):
    """
    Generate an automated report from the selected
    DatasetVersion.
    """

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

    context = reporting_context(request)

    if request.method == "POST":

        form = AutomatedReportForm(
            request.POST,
            user=request.user,
        )

        if form.is_valid():

            dataset = form.cleaned_data["dataset"]
            version = form.cleaned_data.get("version")

            if version is None:
                version = get_selected_version(
                    request,
                    dataset,
                )

            report_name = (
                form.cleaned_data.get(
                    "report_name"
                )
                or f"{dataset.name} Automated Report"
            )

            description = (
                form.cleaned_data.get(
                    "report_description"
                )
                or ""
            )

            try:

                from .services.report_engine import (
                    generate_automated_report,
                )

                report_data = (
                    generate_automated_report(
                        dataset=dataset,
                        version=version,
                    )
                )

                report = Report.objects.create(
                    owner=request.user,
                    dataset=dataset,
                    dataset_version=version,
                    name=report_name,
                    description=description,
                    report_type="Automated",
                    configuration={
                        "dataset_id": dataset.id,
                        "dataset_version_id": version.id,
                    },
                    generated_data=report_data,
                    status="Completed",
                )

                return redirect(
                    "reporting:report_detail",
                    report_id=report.id,
                )

            except Exception as exc:

                form.add_error(
                    None,
                    (
                        "Unable to generate the report: "
                        f"{exc}"
                    ),
                )

    else:

        form = AutomatedReportForm(
            user=request.user,
            initial={
                "dataset": (
                    context["selected_dataset"].id
                    if context["selected_dataset"]
                    else None
                ),
                "version": (
                    context["selected_version"].id
                    if context["selected_version"]
                    else None
                ),
            },
        )

    context["form"] = form

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
    Custom Reports foundation page.

    The complete custom report builder will be implemented
    separately.
    """

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

    context = reporting_context(request)

    form = CustomReportForm(
        request.GET or None,
        user=request.user,
        initial={
            "dataset": (
                context["selected_dataset"].id
                if context["selected_dataset"]
                else None
            ),
            "version": (
                context["selected_version"].id
                if context["selected_version"]
                else None
            ),
        },
    )

    context.update(
        {
            "form": form,
            "custom_reports": (
                CustomReport.objects
                .filter(
                    owner=request.user,
                    is_active=True,
                )
                .select_related(
                    "dataset",
                    "dataset_version",
                )
                .order_by(
                    "-updated_at",
                )
            ),
        }
    )

    return render(
        request,
        "reporting/custom_reports.html",
        context,
    )


# ============================================================
# REPORT HISTORY
# ============================================================
@login_required
def report_history(request):

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

    reports = (
        Report.objects
        .filter(owner=request.user)
        .select_related(
            "dataset",
            "dataset_version",
        )
        .order_by("-created_at")
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    if search_query:

        reports = reports.filter(
            Q(name__icontains=search_query)
            |
            Q(dataset__name__icontains=search_query)
        )


    # --------------------------------------------------------
    # STATUS FILTER
    # --------------------------------------------------------

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    if selected_status:

        reports = reports.filter(
            status=selected_status
        )


    # --------------------------------------------------------
    # REPORT TYPE FILTER
    # --------------------------------------------------------

    selected_report_type = request.GET.get(
        "report_type",
        "",
    ).strip()

    if selected_report_type:

        reports = reports.filter(
            report_type=selected_report_type
        )


    # --------------------------------------------------------
    # REPORT TYPE OPTIONS
    # --------------------------------------------------------

    report_types = (
        Report.objects
        .filter(owner=request.user)
        .values_list(
            "report_type",
            flat=True,
        )
        .distinct()
        .order_by("report_type")
    )


    # --------------------------------------------------------
    # COUNTS
    # --------------------------------------------------------

    user_reports = Report.objects.filter(
        owner=request.user
    )

    completed_count = user_reports.filter(
        status="Completed"
    ).count()

    failed_count = user_reports.filter(
        status="Failed"
    ).count()

    draft_count = user_reports.filter(
        status="Draft"
    ).count()


    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = reporting_context(request)

    context.update(
        {
            "reports": reports,
            "completed_count": completed_count,
            "failed_count": failed_count,
            "draft_count": draft_count,
            "search_query": search_query,
            "selected_status": selected_status,
            "selected_report_type": selected_report_type,
            "report_types": report_types,
        }
    )

    return render(
        request,
        "reporting/report_history.html",
        context,
    )


# ============================================================
# EXPORT CENTER
# ============================================================
@login_required
def export_center(request):

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

    reports = (
        Report.objects
        .filter(owner=request.user)
        .select_related(
            "dataset",
            "dataset_version",
        )
        .order_by("-created_at")
    )

    selected_report = None

    report_id = request.GET.get("report")

    if report_id:
        selected_report = reports.filter(
            id=report_id
        ).first()

    context = reporting_context(request)

    context.update(
        {
            "reports": reports,
            "selected_report": selected_report,
        }
    )

    return render(
        request,
        "reporting/export_center.html",
        context,
    )
# ============================================================
# REPORT DETAIL
# ============================================================

@login_required
def report_detail(request, report_id):
    """
    Display one report belonging to the current user.
    """

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

    report = get_object_or_404(
        Report.objects
        .select_related(
            "dataset",
            "dataset_version",
            "owner",
        )
        .prefetch_related(
            "exports",
        ),
        id=report_id,
        owner=request.user,
    )

    return render(
        request,
        "reporting/report_detail.html",
        {
            "report": report,
        },
    )
# ============================================================
# PDF EXPORT
# ============================================================

@login_required
def export_report_pdf(request, report_id):
    """
    Generate and download a PDF export for a completed report.
    """

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

    report = get_object_or_404(
        Report.objects.select_related(
            "dataset",
            "dataset_version",
        ),
        id=report_id,
        owner=request.user,
    )

    if report.status != "Completed":
        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )

    try:

        from .services.pdf_export import (
            generate_pdf_export,
        )

        export = generate_pdf_export(
            report
        )

        if export.file:

            response = HttpResponse(
                export.file.open("rb").read(),
                content_type="application/pdf",
            )

            response[
                "Content-Disposition"
            ] = (
                'attachment; '
                f'filename="{export.file.name.split("/")[-1]}"'
            )

            return response

    except Exception as exc:

        ReportExport.objects.filter(
            report=report,
            export_type="PDF",
            status="Generating",
        ).update(
            status="Failed",
            error_message=str(exc),
        )

    return redirect(
        "reporting:report_detail",
        report_id=report.id,
    )
# ============================================================
# EXCEL EXPORT
# ============================================================

@login_required
def export_report_excel(request, report_id):
    """
    Generate and download an Excel export
    for a completed report.
    """

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

    report = get_object_or_404(
        Report.objects.select_related(
            "dataset",
            "dataset_version",
        ),
        id=report_id,
        owner=request.user,
    )

    if report.status != "Completed":

        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )

    try:

        from .services.excel_export import (
            generate_excel_export,
        )

        export = generate_excel_export(
            report
        )

        if export.file:

            response = HttpResponse(
                export.file.open("rb").read(),
                content_type=(
                    "application/vnd.openxmlformats-"
                    "officedocument.spreadsheetml.sheet"
                ),
            )

            response[
                "Content-Disposition"
            ] = (
                "attachment; "
                f'filename="{export.file.name.split("/")[-1]}"'
            )

            return response

    except Exception as exc:

        ReportExport.objects.filter(
            report=report,
            export_type="Excel",
            status="Generating",
        ).update(
            status="Failed",
            error_message=str(exc),
        )

    return redirect(
        "reporting:report_detail",
        report_id=report.id,
    )
# ============================================================
# EXPORT HISTORY
# ============================================================

@login_required
def export_history(request):
    """
    Display all PDF and Excel exports belonging
    to the current user's reports.
    """

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

    exports = (
        ReportExport.objects
        .filter(
            report__owner=request.user,
        )
        .select_related(
            "report",
            "report__dataset",
            "report__dataset_version",
        )
        .order_by(
            "-created_at",
        )
    )

    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    search_query = request.GET.get(
        "search",
        "",
    ).strip()

    if search_query:

        exports = exports.filter(
            Q(
                report__name__icontains=search_query
            )
            |
            Q(
                report__dataset__name__icontains=search_query
            )
        )

    # --------------------------------------------------------
    # EXPORT TYPE
    # --------------------------------------------------------

    selected_type = request.GET.get(
        "export_type",
        "",
    ).strip()

    if selected_type in {
        "PDF",
        "Excel",
    }:

        exports = exports.filter(
            export_type=selected_type,
        )

    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------

    selected_status = request.GET.get(
        "status",
        "",
    ).strip()

    if selected_status in {
        "Generating",
        "Completed",
        "Failed",
    }:

        exports = exports.filter(
            status=selected_status,
        )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = reporting_context(request)

    context.update(
        {
            "exports": exports,
            "search_query": search_query,
            "selected_type": selected_type,
            "selected_status": selected_status,
        }
    )

    return render(
        request,
        "reporting/export_history.html",
        context,
    )

# ============================================================
# PDF EXPORT
# ============================================================

@login_required
def export_pdf(request, report_id):

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

    report = get_object_or_404(
        Report.objects.select_related(
            "dataset",
            "dataset_version",
        ),
        id=report_id,
        owner=request.user,
    )

    export = ReportExport.objects.create(
        report=report,
        export_type="PDF",
        status="Generating",
    )

    try:

        from .services.export_engine import (
            generate_pdf_export,
        )

        pdf_bytes = generate_pdf_export(report)

        filename = (
            f"report_{report.id}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )

        export.file.save(
            filename,
            ContentFile(pdf_bytes),
            save=False,
        )

        export.status = "Completed"
        export.completed_at = timezone.now()
        export.error_message = ""

        export.save()

        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )

    except Exception as exc:

        export.status = "Failed"
        export.error_message = str(exc)
        export.save()

        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )


# ============================================================
# EXCEL EXPORT
# ============================================================

@login_required
def export_excel(request, report_id):

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

    report = get_object_or_404(
        Report.objects.select_related(
            "dataset",
            "dataset_version",
        ),
        id=report_id,
        owner=request.user,
    )

    export = ReportExport.objects.create(
        report=report,
        export_type="Excel",
        status="Generating",
    )

    try:

        from .services.export_engine import (
            generate_excel_export,
        )

        excel_bytes = generate_excel_export(report)

        filename = (
            f"report_{report.id}_"
            f"{timezone.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        )

        export.file.save(
            filename,
            ContentFile(excel_bytes),
            save=False,
        )

        export.status = "Completed"
        export.completed_at = timezone.now()
        export.error_message = ""

        export.save()

        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )

    except Exception as exc:

        export.status = "Failed"
        export.error_message = str(exc)
        export.save()

        return redirect(
            "reporting:report_detail",
            report_id=report.id,
        )