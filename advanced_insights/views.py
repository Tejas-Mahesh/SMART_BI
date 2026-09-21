from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from urllib.parse import urlencode
from data_management.models import Dataset, DatasetVersion
from data_management.views import (
    read_dataset_file,
    read_dataset_version_file,
)
import pandas as pd
from .models import (
    InsightRun,
    TrendResult,
    ForecastResult,
    AnomalyResult,
     RootCauseResult,
      ChurnRiskResult
)
from .services.future_trends import (
    analyze_future_trend,
    detect_date_columns,
    detect_numeric_columns,
)

from .services.forecasting import (
    analyze_forecast,
)
from .services.anomaly_detection import (
    analyze_anomalies,
    detect_date_columns,
    detect_numeric_columns,
)
from .services.anomaly_detection import (
    analyze_anomalies,
)
from .services.root_cause_analysis import analyze_root_causes
from django.utils import timezone
from .models import InsightRun, CustomerSegmentationResult
from .segmentation import analyze_customer_segments
from .churn import (
    analyze_churn_risk,
    detect_customer_column,
    detect_date_column,
    detect_activity_metrics,
)
from .models import (
    InsightRun,
    OpportunityDetectionResult,
)

from .opportunity import (
    analyze_opportunity_detection,
)
def _future_trends_url(
    dataset,
    version=None,
    date_column=None,
    metric_column=None,
    frequency=None,
):

    params = {
        "dataset": dataset.id,
    }

    if version:
        params["version"] = version.id

    if date_column:
        params["date_column"] = date_column

    if metric_column:
        params["metric_column"] = metric_column

    if frequency:
        params["frequency"] = frequency

    query_string = urlencode(params)

    return (
        "/advanced-insights/future-trends/"
        f"?{query_string}"
    )
def _forecasting_url(
    dataset,
    version=None,
    date_column=None,
    metric_column=None,
    frequency=None,
    method=None,
    horizon=None,
):

    params = {
        "dataset": dataset.id,
    }

    if version:
        params["version"] = version.id

    if date_column:
        params["date_column"] = date_column

    if metric_column:
        params["metric_column"] = metric_column

    if frequency:
        params["frequency"] = frequency

    if method:
        params["method"] = method

    if horizon:
        params["horizon"] = horizon

    query_string = urlencode(
        params
    )

    return (
        "/advanced-insights/forecasting/"
        f"?{query_string}"
    )
# ============================================================
# ANOMALY DETECTION URL BUILDER
# ============================================================

def _anomaly_detection_url(
    dataset,
    version=None,
    date_column=None,
    metric_column=None,
    threshold=None,
):
    params = {
        "dataset": dataset.id,
    }

    if version:
        params["version"] = version.id

    if date_column:
        params["date_column"] = date_column

    if metric_column:
        params["metric_column"] = metric_column

    if threshold is not None:
        params["threshold"] = threshold

    query_string = urlencode(params)

    return (
        "/advanced-insights/anomaly-detection/"
        f"?{query_string}"
    )
# ============================================================
# COMMON APPROVAL CHECK
# ============================================================

def user_is_approved(request):

    if not request.user.is_authenticated:
        return False

    return (
        getattr(
            request.user,
            "approval_status",
            ""
        )
        == "Approved"
    )


# ============================================================
# FUTURE TRENDS
# ============================================================

@login_required
def future_trends(request):

    # --------------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------------

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            }
        )

    # --------------------------------------------------------
    # USER DATASETS
    # --------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None

    versions = []

    date_columns = []
    numeric_columns = []

    selected_date_column = ""
    selected_metric_column = ""
    selected_frequency = "M"

    trend_result = None
    analysis_error = None

    # --------------------------------------------------------
    # DATASET SELECTION
    # --------------------------------------------------------

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(
                id=dataset_id
            )
            .first()
        )

    elif datasets.exists():

        selected_dataset = (
            datasets.first()
        )

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by(
                "-version_number"
            )
        )

        requested_version = request.GET.get(
            "version"
        )

        # ----------------------------------------------------
        # 1. EXPLICIT VERSION
        # ----------------------------------------------------

        if requested_version:

            selected_version = (
                versions
                .filter(
                    id=requested_version
                )
                .first()
            )

        # ----------------------------------------------------
        # 2. CURRENT VERSION
        # ----------------------------------------------------

        if selected_version is None:

            selected_version = (
                versions
                .filter(
                    is_current=True
                )
                .first()
            )

        # ----------------------------------------------------
        # 3. LATEST VERSION
        # ----------------------------------------------------

        if selected_version is None:

            selected_version = (
                versions.first()
            )

    # --------------------------------------------------------
    # LOAD SELECTED DATASET VERSION
    # --------------------------------------------------------

    dataframe = None

    if selected_dataset:

        try:

            if selected_version:

                dataframe = (
                    read_dataset_version_file(
                        selected_version
                    )
                )

            else:

                dataframe = (
                    read_dataset_file(
                        selected_dataset
                    )
                )

            # ------------------------------------------------
            # NORMALIZE COLUMN NAMES
            # ------------------------------------------------

            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

            # ------------------------------------------------
            # DETECT AVAILABLE COLUMNS
            # ------------------------------------------------

            date_columns = (
                detect_date_columns(
                    dataframe
                )
            )

            numeric_columns = (
                detect_numeric_columns(
                    dataframe
                )
            )

        except Exception as error:

            analysis_error = (
                f"Unable to load dataset: {error}"
            )

    # ========================================================
    # POST — RUN FUTURE TRENDS
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # DATASET MUST EXIST
        # ----------------------------------------------------

        if selected_dataset is None:

            messages.error(
                request,
                "Please select a dataset."
            )

            return redirect(
                "advanced_insights:future_trends"
            )

        # ----------------------------------------------------
        # GET POST PARAMETERS
        # ----------------------------------------------------

        selected_date_column = (
            request.POST.get(
                "date_column",
                ""
            )
            .strip()
        )

        selected_metric_column = (
            request.POST.get(
                "metric_column",
                ""
            )
            .strip()
        )

        selected_frequency = (
            request.POST.get(
                "frequency",
                "M"
            )
            .strip()
            .upper()
        )

        # ----------------------------------------------------
        # VALIDATE DATE COLUMN
        # ----------------------------------------------------

        if not selected_date_column:

            messages.error(
                request,
                "Please select a date column."
            )

            return redirect(
                _future_trends_url(
                    selected_dataset,
                    selected_version,
                )
            )

        if selected_date_column not in date_columns:

            messages.error(
                request,
                "The selected date column is not available "
                "in this dataset version."
            )

            return redirect(
                _future_trends_url(
                    selected_dataset,
                    selected_version,
                )
            )

        # ----------------------------------------------------
        # VALIDATE METRIC
        # ----------------------------------------------------

        if not selected_metric_column:

            messages.error(
                request,
                "Please select a numeric metric."
            )

            return redirect(
                _future_trends_url(
                    selected_dataset,
                    selected_version,
                )
            )

        if selected_metric_column not in numeric_columns:

            messages.error(
                request,
                "The selected metric is not available "
                "as a numeric column in this dataset version."
            )

            return redirect(
                _future_trends_url(
                    selected_dataset,
                    selected_version,
                )
            )

        # ----------------------------------------------------
        # VALIDATE FREQUENCY
        # ----------------------------------------------------

        allowed_frequencies = {
            "D",
            "W",
            "M",
            "Q",
            "Y",
        }

        if selected_frequency not in allowed_frequencies:

            messages.error(
                request,
                "Invalid trend frequency selected."
            )

            return redirect(
                _future_trends_url(
                    selected_dataset,
                    selected_version,
                )
            )

        # ----------------------------------------------------
        # SOURCE VERSION
        # ----------------------------------------------------

        if selected_version is None:

            messages.error(
                request,
                "No dataset version is available for analysis."
            )

            return redirect(
                "advanced_insights:future_trends"
            )

        # ----------------------------------------------------
        # CREATE INSIGHT RUN
        # ----------------------------------------------------

        insight_run = InsightRun.objects.create(

            dataset=selected_dataset,

            dataset_version=selected_version,

            insight_type="Future Trends",

            status="Running",

            parameters={
                "date_column":
                    selected_date_column,

                "metric_column":
                    selected_metric_column,

                "frequency":
                    selected_frequency,
            },

            created_by=request.user,
        )

        # ----------------------------------------------------
        # RUN ANALYSIS
        # ----------------------------------------------------

        try:

            trend_result_data = (
                analyze_future_trend(
                    dataframe=dataframe,
                    date_column=selected_date_column,
                    metric_column=selected_metric_column,
                    frequency=selected_frequency,
                )
            )

            # ------------------------------------------------
            # SAVE TREND RESULT
            # ------------------------------------------------

            trend_result = TrendResult.objects.create(

                insight_run=insight_run,

                date_column=(
                    trend_result_data[
                        "date_column"
                    ]
                ),

                metric_column=(
                    trend_result_data[
                        "metric_column"
                    ]
                ),

                frequency=(
                    trend_result_data[
                        "frequency"
                    ]
                ),

                trend_direction=(
                    trend_result_data[
                        "trend_direction"
                    ]
                ),

                trend_strength=(
                    trend_result_data[
                        "trend_strength"
                    ]
                ),

                percentage_change=(
                    trend_result_data[
                        "percentage_change"
                    ]
                ),

                average_value=(
                    trend_result_data[
                        "average_value"
                    ]
                ),

                minimum_value=(
                    trend_result_data[
                        "minimum_value"
                    ]
                ),

                maximum_value=(
                    trend_result_data[
                        "maximum_value"
                    ]
                ),

                first_period_value=(
                    trend_result_data[
                        "first_period_value"
                    ]
                ),

                latest_period_value=(
                    trend_result_data[
                        "latest_period_value"
                    ]
                ),

                recent_direction=(
                    trend_result_data[
                        "recent_direction"
                    ]
                ),

                summary=(
                    trend_result_data[
                        "summary"
                    ]
                ),

                chart_data=(
                    trend_result_data[
                        "chart_data"
                    ]
                ),
            )

            # ------------------------------------------------
            # COMPLETE INSIGHT RUN
            # ------------------------------------------------

            insight_run.status = "Completed"

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            messages.success(
                request,
                (
                    "Future Trends analysis completed "
                    "successfully."
                )
            )

        except Exception as error:

            # ------------------------------------------------
            # SAVE FAILURE
            # ------------------------------------------------

            insight_run.status = "Failed"

            insight_run.error_message = str(
                error
            )

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            messages.error(
                request,
                (
                    "Future Trends analysis failed: "
                    f"{error}"
                )
            )

    # ========================================================
    # DEFAULT SELECTIONS FOR GET
    # ========================================================

    if date_columns:

        requested_date_column = request.GET.get(
            "date_column"
        )

        if (
            requested_date_column
            and
            requested_date_column in date_columns
        ):

            selected_date_column = (
                requested_date_column
            )

        elif not selected_date_column:

            selected_date_column = (
                date_columns[0]
            )

    if numeric_columns:

        requested_metric_column = request.GET.get(
            "metric_column"
        )

        if (
            requested_metric_column
            and
            requested_metric_column in numeric_columns
        ):

            selected_metric_column = (
                requested_metric_column
            )

        elif not selected_metric_column:

            selected_metric_column = (
                numeric_columns[0]
            )

    requested_frequency = request.GET.get(
        "frequency"
    )

    if requested_frequency:

        requested_frequency = (
            requested_frequency
            .strip()
            .upper()
        )

        if requested_frequency in {
            "D",
            "W",
            "M",
            "Q",
            "Y",
        }:

            selected_frequency = (
                requested_frequency
            )

    # ========================================================
    # LATEST COMPLETED TREND RESULT
    # ========================================================

    latest_run = None

    if selected_dataset:

        latest_run = (
            InsightRun.objects
            .filter(
                dataset=selected_dataset,
                dataset_version=selected_version,
                insight_type="Future Trends",
                status="Completed",
                created_by=request.user,
            )
            .select_related(
                "trend_result",
                "dataset_version",
            )
            .order_by(
                "-started_at"
            )
            .first()
        )

    if latest_run:

        trend_result = (
            latest_run.trend_result
        )

    # ========================================================
    # VERSION DISPLAY INFORMATION
    # ========================================================

    version_label = "Original"
    version_badge = "original"

    if selected_version:

        version_type = (
            getattr(
                selected_version,
                "version_type",
                "",
            )
            or ""
        )

        if version_type.lower() == "cleaned":

            version_label = "Cleaned"
            version_badge = "cleaned"

        elif version_type.lower() == "transformed":

            version_label = "Transformed"
            version_badge = "transformed"

        elif version_type.lower() == "validated":

            version_label = "Validated"
            version_badge = "validated"

        elif version_type.lower() == "original":

            version_label = "Original"
            version_badge = "original"

        else:

            version_label = (
                version_type
                or
                (
                    f"Version "
                    f"{selected_version.version_number}"
                )
            )

            version_badge = "version"

    # ========================================================
    # FREQUENCY OPTIONS
    # ========================================================

    frequency_options = [
        {
            "value": "D",
            "label": "Daily",
        },
        {
            "value": "W",
            "label": "Weekly",
        },
        {
            "value": "M",
            "label": "Monthly",
        },
        {
            "value": "Q",
            "label": "Quarterly",
        },
        {
            "value": "Y",
            "label": "Yearly",
        },
    ]

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "advanced_insights/future_trends.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "selected_version":
                selected_version,

            "versions":
                versions,

            "date_columns":
                date_columns,

            "numeric_columns":
                numeric_columns,

            "selected_date_column":
                selected_date_column,

            "selected_metric_column":
                selected_metric_column,

            "selected_frequency":
                selected_frequency,

            "frequency_options":
                frequency_options,

            "trend_result":
                trend_result,

            "latest_run":
                latest_run,

            "analysis_error":
                analysis_error,

            "version_label":
                version_label,

            "version_badge":
                version_badge,
        }
    )

# ============================================================
# FUTURE TRENDS HISTORY
# ============================================================

@login_required
def future_trends_history(request):

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            }
        )

    history = (
        InsightRun.objects
        .filter(
            created_by=request.user,
            insight_type="Future Trends",
        )
        .select_related(
            "dataset",
            "dataset_version",
            "trend_result",
        )
        .order_by(
            "-started_at"
        )
    )

    return render(
        request,
        "advanced_insights/future_trends_history.html",
        {
            "history": history,
        }
    )

# ============================================================
# FORECASTING
# ============================================================

@login_required
def forecasting(request):

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            }
        )

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    dataframe = None

    date_columns = []
    numeric_columns = []

    # --------------------------------------------------------
    # DATASET SELECTION
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    if selected_dataset is None:

        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------

    if selected_dataset:

        version_id = request.GET.get("version")

        if version_id:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    id=version_id,
                    dataset=selected_dataset,
                )
                .first()
            )

        if selected_version is None:

            selected_version = (
                selected_dataset.versions
                .filter(
                    is_current=True,
                )
                .first()
            )

        if selected_version is None:

            selected_version = (
                selected_dataset.versions
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

    # --------------------------------------------------------
    # READ SELECTED VERSION
    # --------------------------------------------------------

    if selected_version:

        try:

            dataframe = read_dataset_version_file(
                selected_version
            )

            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

            date_columns = detect_date_columns(
                dataframe
            )

            numeric_columns = detect_numeric_columns(
                dataframe
            )

        except Exception as exc:

            messages.error(
                request,
                (
                    "Unable to read the selected dataset "
                    f"version: {exc}"
                )
            )

    # --------------------------------------------------------
    # POST — RUN FORECAST
    # --------------------------------------------------------

    if request.method == "POST":

        if not selected_dataset:

            messages.error(
                request,
                "Please select a dataset."
            )

            return redirect(
                "advanced_insights:forecasting"
            )

        if not selected_version:

            messages.error(
                request,
                "Please select a dataset version."
            )

            return redirect(
                "advanced_insights:forecasting"
            )

        date_column = (
            request.POST.get(
                "date_column",
                ""
            ).strip()
        )

        metric_column = (
            request.POST.get(
                "metric_column",
                ""
            ).strip()
        )

        frequency = (
            request.POST.get(
                "frequency",
                "M"
            ).strip().upper()
        )

        method = (
            request.POST.get(
                "method",
                "Linear Trend"
            ).strip()
        )

        horizon_raw = (
            request.POST.get(
                "horizon",
                "3"
            ).strip()
        )

        if not date_column:

            messages.error(
                request,
                "Please select a date column."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon_raw,
                )
            )

        if not metric_column:

            messages.error(
                request,
                "Please select a numeric metric."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon_raw,
                )
            )

        if date_column not in date_columns:

            messages.error(
                request,
                "The selected date column is invalid."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon_raw,
                )
            )

        if metric_column not in numeric_columns:

            messages.error(
                request,
                "The selected metric column is invalid."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon_raw,
                )
            )

        try:

            horizon = int(
                horizon_raw
            )

        except (TypeError, ValueError):

            messages.error(
                request,
                "Forecast horizon must be a valid number."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    3,
                )
            )

        # ----------------------------------------------------
        # CREATE INSIGHT RUN
        # ----------------------------------------------------

        insight_run = InsightRun.objects.create(

            dataset=selected_dataset,

            dataset_version=selected_version,

            insight_type="Forecasting",

            status="Running",

            parameters={
                "date_column": date_column,
                "metric_column": metric_column,
                "frequency": frequency,
                "method": method,
                "horizon": horizon,
            },

            created_by=request.user,
        )

        try:

            # ------------------------------------------------
            # RUN FORECASTING ENGINE
            # ------------------------------------------------

            result = analyze_forecast(

                dataframe=dataframe,

                date_column=date_column,

                metric_column=metric_column,

                frequency=frequency,

                method=method,

                horizon=horizon,
            )

            # ------------------------------------------------
            # SAVE FORECAST RESULT
            # ------------------------------------------------

            ForecastResult.objects.create(

                insight_run=insight_run,

                date_column=result[
                    "date_column"
                ],

                metric_column=result[
                    "metric_column"
                ],

                frequency=result[
                    "frequency"
                ],

                method=result[
                    "method"
                ],

                horizon=result[
                    "horizon"
                ],

                historical_periods=result[
                    "historical_periods"
                ],

                forecast_periods=result[
                    "forecast_periods"
                ],

                last_actual_value=result[
                    "last_actual_value"
                ],

                first_forecast_value=result[
                    "first_forecast_value"
                ],

                latest_forecast_value=result[
                    "latest_forecast_value"
                ],

                forecast_change_percentage=result[
                    "forecast_change_percentage"
                ],

                average_forecast_value=result[
                    "average_forecast_value"
                ],

                minimum_forecast_value=result[
                    "minimum_forecast_value"
                ],

                maximum_forecast_value=result[
                    "maximum_forecast_value"
                ],

                confidence_level=result[
                    "confidence_level"
                ],

                summary=result[
                    "summary"
                ],

                chart_data=result[
                    "chart_data"
                ],
            )

            # ------------------------------------------------
            # COMPLETE RUN
            # ------------------------------------------------

            insight_run.status = "Completed"

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            messages.success(
                request,
                "Forecasting analysis completed successfully."
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon,
                )
            )

        except Exception as exc:

            # ------------------------------------------------
            # FAILED RUN
            # ------------------------------------------------

            insight_run.status = "Failed"

            insight_run.error_message = str(
                exc
            )

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            messages.error(
                request,
                (
                    "Forecasting could not be completed: "
                    f"{exc}"
                )
            )

            return redirect(
                _forecasting_url(
                    selected_dataset,
                    selected_version,
                    date_column,
                    metric_column,
                    frequency,
                    method,
                    horizon,
                )
            )

    # --------------------------------------------------------
    # RESTORE SELECTED PARAMETERS
    # --------------------------------------------------------

    selected_date_column = (
        request.GET.get(
            "date_column",
            ""
        )
    )

    selected_metric_column = (
        request.GET.get(
            "metric_column",
            ""
        )
    )

    selected_frequency = (
        request.GET.get(
            "frequency",
            "M"
        ).strip().upper()
    )

    selected_method = (
        request.GET.get(
            "method",
            "Linear Trend"
        ).strip()
    )

    selected_horizon = (
        request.GET.get(
            "horizon",
            "3"
        ).strip()
    )

    # --------------------------------------------------------
    # LATEST COMPLETED FORECAST
    # --------------------------------------------------------

    forecast_result = None
    latest_run = None

    if selected_dataset and selected_version:

        latest_run = (
            InsightRun.objects
            .filter(
                created_by=request.user,
                dataset=selected_dataset,
                dataset_version=selected_version,
                insight_type="Forecasting",
                status="Completed",
            )
            .select_related(
                "forecast_result",
            )
            .order_by(
                "-started_at"
            )
            .first()
        )

        if latest_run:

            forecast_result = getattr(
                latest_run,
                "forecast_result",
                None
            )

    # --------------------------------------------------------
    # DATASET VERSION LABEL
    # --------------------------------------------------------

    version_label = None

    if selected_version:

        version_label = (
            f"Version "
            f"{selected_version.version_number}"
        )

        if selected_version.version_type:

            version_label += (
                f" • "
                f"{selected_version.version_type}"
            )

    # --------------------------------------------------------
    # FORECAST OPTIONS
    # --------------------------------------------------------

    frequency_options = [
        ("D", "Daily"),
        ("W", "Weekly"),
        ("M", "Monthly"),
        ("Q", "Quarterly"),
        ("Y", "Yearly"),
    ]

    method_options = [
        (
            "Linear Trend",
            "Linear Trend",
        ),
        (
            "Moving Average",
            "Moving Average",
        ),
    ]

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "advanced_insights/forecasting.html",
        {
            "datasets": datasets,

            "selected_dataset": selected_dataset,

            "selected_version": selected_version,

            "date_columns": date_columns,

            "numeric_columns": numeric_columns,

            "selected_date_column": (
                selected_date_column
            ),

            "selected_metric_column": (
                selected_metric_column
            ),

            "selected_frequency": (
                selected_frequency
            ),

            "selected_method": (
                selected_method
            ),

            "selected_horizon": (
                selected_horizon
            ),

            "forecast_result": (
                forecast_result
            ),

            "latest_run": latest_run,

            "version_label": version_label,

            "frequency_options": (
                frequency_options
            ),

            "method_options": (
                method_options
            ),
        }
    )

# ============================================================
# ANOMALY DETECTION
# ============================================================

@login_required
def anomaly_detection(request):

    # --------------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------------

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            }
        )

    # --------------------------------------------------------
    # USER DATASETS
    # --------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by(
            "-uploaded_at"
        )
    )

    selected_dataset = None
    selected_version = None

    versions = []

    dataframe = None

    date_columns = []
    numeric_columns = []

    selected_date_column = ""
    selected_metric_column = ""

    selected_threshold = "2.5"

    anomaly_result = None
    latest_run = None

    analysis_error = None

    # ========================================================
    # DATASET SELECTION
    # ========================================================

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(
                id=dataset_id
            )
            .first()
        )

    elif datasets.exists():

        selected_dataset = datasets.first()

    # ========================================================
    # VERSION SELECTION
    # ========================================================

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by(
                "-version_number"
            )
        )

        requested_version = request.GET.get(
            "version"
        )

        # ----------------------------------------------------
        # 1. EXPLICIT VERSION
        # ----------------------------------------------------

        if requested_version:

            selected_version = (
                versions
                .filter(
                    id=requested_version
                )
                .first()
            )

        # ----------------------------------------------------
        # 2. CURRENT VERSION
        # ----------------------------------------------------

        if selected_version is None:

            selected_version = (
                versions
                .filter(
                    is_current=True
                )
                .first()
            )

        # ----------------------------------------------------
        # 3. LATEST VERSION
        # ----------------------------------------------------

        if selected_version is None:

            selected_version = (
                versions.first()
            )

    # ========================================================
    # READ SELECTED DATASET VERSION
    # ========================================================

    if selected_version:

        try:

            dataframe = (
                read_dataset_version_file(
                    selected_version
                )
            )

            # ------------------------------------------------
            # NORMALIZE COLUMN NAMES
            # ------------------------------------------------

            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

            # ------------------------------------------------
            # DETECT AVAILABLE COLUMNS
            # ------------------------------------------------

            date_columns = (
                detect_date_columns(
                    dataframe
                )
            )

            numeric_columns = (
                detect_numeric_columns(
                    dataframe
                )
            )

        except Exception as exc:

            analysis_error = (
                "Unable to load the selected dataset "
                f"version: {exc}"
            )

    # ========================================================
    # RESTORE GET PARAMETERS
    # ========================================================

    requested_date_column = (
        request.GET.get(
            "date_column",
            ""
        ).strip()
    )

    if (
        requested_date_column
        and
        requested_date_column in date_columns
    ):

        selected_date_column = (
            requested_date_column
        )

    elif date_columns:

        selected_date_column = (
            date_columns[0]
        )

    requested_metric_column = (
        request.GET.get(
            "metric_column",
            ""
        ).strip()
    )

    if (
        requested_metric_column
        and
        requested_metric_column in numeric_columns
    ):

        selected_metric_column = (
            requested_metric_column
        )

    elif numeric_columns:

        selected_metric_column = (
            numeric_columns[0]
        )

    requested_threshold = (
        request.GET.get(
            "threshold",
            "2.5"
        ).strip()
    )

    if requested_threshold:

        selected_threshold = (
            requested_threshold
        )

    # ========================================================
    # POST — RUN ANOMALY DETECTION
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # DATASET VALIDATION
        # ----------------------------------------------------

        if selected_dataset is None:

            messages.error(
                request,
                "Please select a dataset."
            )

            return redirect(
                "advanced_insights:anomaly_detection"
            )

        # ----------------------------------------------------
        # VERSION VALIDATION
        # ----------------------------------------------------

        if selected_version is None:

            messages.error(
                request,
                "Please select a dataset version."
            )

            return redirect(
                "advanced_insights:anomaly_detection"
            )

        # ----------------------------------------------------
        # POST PARAMETERS
        # ----------------------------------------------------

        selected_date_column = (
            request.POST.get(
                "date_column",
                ""
            ).strip()
        )

        selected_metric_column = (
            request.POST.get(
                "metric_column",
                ""
            ).strip()
        )

        selected_threshold = (
            request.POST.get(
                "threshold",
                "2.5"
            ).strip()
        )

        # ----------------------------------------------------
        # DATE COLUMN
        # ----------------------------------------------------

        if (
            selected_date_column
            and
            selected_date_column not in date_columns
        ):

            messages.error(
                request,
                (
                    "The selected date column is not "
                    "available in this dataset version."
                )
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    selected_threshold,
                )
            )

        # ----------------------------------------------------
        # METRIC COLUMN
        # ----------------------------------------------------

        if not selected_metric_column:

            messages.error(
                request,
                "Please select a numeric metric."
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    selected_threshold,
                )
            )

        if (
            selected_metric_column
            not in numeric_columns
        ):

            messages.error(
                request,
                (
                    "The selected metric column is not "
                    "available as a numeric column in "
                    "this dataset version."
                )
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    selected_threshold,
                )
            )

        # ----------------------------------------------------
        # THRESHOLD VALIDATION
        # ----------------------------------------------------

        try:

            threshold = float(
                selected_threshold
            )

        except (
            TypeError,
            ValueError,
        ):

            messages.error(
                request,
                "Anomaly threshold must be a valid number."
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    "2.5",
                )
            )

        if threshold <= 0:

            messages.error(
                request,
                "Anomaly threshold must be greater than 0."
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    "2.5",
                )
            )

        # ----------------------------------------------------
        # CREATE INSIGHT RUN
        # ----------------------------------------------------

        insight_run = InsightRun.objects.create(

            dataset=selected_dataset,

            dataset_version=selected_version,

            insight_type="Anomaly Detection",

            status="Running",

            parameters={
                "date_column": (
                    selected_date_column
                ),

                "metric_column": (
                    selected_metric_column
                ),

                "threshold": threshold,

                "detection_method": (
                    "Z-Score"
                ),
            },

            created_by=request.user,
        )

        # ====================================================
        # RUN ANALYSIS
        # ====================================================

        try:

            result = analyze_anomalies(

                dataframe=dataframe,

                metric_column=(
                    selected_metric_column
                ),

                threshold=threshold,

                date_column=(
                    selected_date_column
                    or None
                ),
            )

            # ------------------------------------------------
            # SAVE ANOMALY RESULT
            # ------------------------------------------------

            AnomalyResult.objects.create(

                insight_run=insight_run,

                date_column=result[
                    "date_column"
                ],

                metric_column=result[
                    "metric_column"
                ],

                detection_method=result[
                    "detection_method"
                ],

                threshold=result[
                    "threshold"
                ],

                total_records=result[
                    "total_records"
                ],

                normal_records=result[
                    "normal_records"
                ],

                anomaly_count=result[
                    "anomaly_count"
                ],

                anomaly_percentage=result[
                    "anomaly_percentage"
                ],

                average_value=result[
                    "average_value"
                ],

                standard_deviation=result[
                    "standard_deviation"
                ],

                minimum_value=result[
                    "minimum_value"
                ],

                maximum_value=result[
                    "maximum_value"
                ],

                highest_anomaly_value=result[
                    "highest_anomaly_value"
                ],

                lowest_anomaly_value=result[
                    "lowest_anomaly_value"
                ],

                summary=result[
                    "summary"
                ],

                chart_data=result[
                    "chart_data"
                ],

                anomaly_data=result[
                    "anomaly_data"
                ],
            )

            # ------------------------------------------------
            # COMPLETE RUN
            # ------------------------------------------------

            insight_run.status = (
                "Completed"
            )

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            messages.success(
                request,
                (
                    "Anomaly Detection analysis "
                    "completed successfully."
                )
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    threshold,
                )
            )

        except Exception as exc:

            # ------------------------------------------------
            # FAILED RUN
            # ------------------------------------------------

            insight_run.status = (
                "Failed"
            )

            insight_run.error_message = str(
                exc
            )

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            messages.error(
                request,
                (
                    "Anomaly Detection could not "
                    f"be completed: {exc}"
                )
            )

            return redirect(
                _anomaly_detection_url(
                    selected_dataset,
                    selected_version,
                    selected_date_column,
                    selected_metric_column,
                    selected_threshold,
                )
            )

    # ========================================================
    # LATEST COMPLETED ANOMALY RESULT
    # ========================================================

    if (
        selected_dataset
        and
        selected_version
    ):

        latest_run = (
            InsightRun.objects
            .filter(
                created_by=request.user,

                dataset=selected_dataset,

                dataset_version=selected_version,

                insight_type="Anomaly Detection",

                status="Completed",
            )
            .select_related(
                "anomaly_result",
                "dataset_version",
            )
            .order_by(
                "-started_at"
            )
            .first()
        )

        if latest_run:

            anomaly_result = (
                getattr(
                    latest_run,
                    "anomaly_result",
                    None
                )
            )

    # ========================================================
    # VERSION DISPLAY
    # ========================================================

    version_label = None

    if selected_version:

        version_label = (
            f"Version "
            f"{selected_version.version_number}"
        )

        if selected_version.version_type:

            version_label += (
                " • "
                f"{selected_version.version_type}"
            )

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "advanced_insights/anomaly_detection.html",
        {
            "datasets": datasets,

            "selected_dataset": (
                selected_dataset
            ),

            "selected_version": (
                selected_version
            ),

            "versions": versions,

            "date_columns": (
                date_columns
            ),

            "numeric_columns": (
                numeric_columns
            ),

            "selected_date_column": (
                selected_date_column
            ),

            "selected_metric_column": (
                selected_metric_column
            ),

            "selected_threshold": (
                selected_threshold
            ),

            "anomaly_result": (
                anomaly_result
            ),

            "latest_run": (
                latest_run
            ),

            "version_label": (
                version_label
            ),

            "analysis_error": (
                analysis_error
            ),
        }
    )
from urllib.parse import urlencode

import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from data_management.models import Dataset, DatasetVersion
from .models import InsightRun, RootCauseResult
from .services.root_cause_analysis import analyze_root_causes


# ============================================================
# ROOT CAUSE ANALYSIS
# ============================================================

@login_required
def root_cause_analysis(request):

    # --------------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # AVAILABLE DATASETS
    # --------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if not datasets.exists():
        messages.warning(
            request,
            "Please upload a dataset before using Root Cause Analysis.",
        )

        return render(
            request,
            "advanced_insights/root_cause_analysis.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "versions": [],
                "selected_version": None,
                "numeric_columns": [],
                "dimension_columns": [],
                "date_columns": [],
                "available_periods": [],
                "selected_metric_column": "",
                "selected_dimension_column": "",
                "selected_date_column": "",
                "selected_target_period": "",
                "selected_comparison_period": "",
                "root_cause_result": None,
            },
        )

    # --------------------------------------------------------
    # SELECT DATASET
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    selected_dataset = None

    if dataset_id:
        try:
            selected_dataset = datasets.get(
                id=dataset_id
            )
        except Dataset.DoesNotExist:
            selected_dataset = None

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # AVAILABLE VERSIONS
    # --------------------------------------------------------

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    if not versions.exists():
        messages.warning(
            request,
            "The selected dataset does not have any versions.",
        )

        return render(
            request,
            "advanced_insights/root_cause_analysis.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "versions": versions,
                "selected_version": None,
                "numeric_columns": [],
                "dimension_columns": [],
                "date_columns": [],
                "available_periods": [],
                "selected_metric_column": "",
                "selected_dimension_column": "",
                "selected_date_column": "",
                "selected_target_period": "",
                "selected_comparison_period": "",
                "root_cause_result": None,
            },
        )

    # --------------------------------------------------------
    # SELECT VERSION
    # --------------------------------------------------------

    version_id = request.GET.get("version")

    selected_version = None

    if version_id:
        try:
            selected_version = versions.get(
                id=version_id
            )
        except DatasetVersion.DoesNotExist:
            selected_version = None

    if selected_version is None:
        selected_version = (
            versions
            .filter(is_current=True)
            .first()
        )

    if selected_version is None:
        selected_version = versions.first()

    # --------------------------------------------------------
    # READ SELECTED DATASET VERSION
    # --------------------------------------------------------

    try:

        dataframe = read_dataset_version_file(
            selected_version
        )

    except Exception as exc:

        messages.error(
            request,
            f"Unable to read the selected dataset version: {exc}",
        )

        return render(
            request,
            "advanced_insights/root_cause_analysis.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "versions": versions,
                "selected_version": selected_version,
                "numeric_columns": [],
                "dimension_columns": [],
                "date_columns": [],
                "available_periods": [],
                "selected_metric_column": "",
                "selected_dimension_column": "",
                "selected_date_column": "",
                "selected_target_period": "",
                "selected_comparison_period": "",
                "root_cause_result": None,
            },
        )

    # --------------------------------------------------------
    # DETECT COLUMNS
    # --------------------------------------------------------

    numeric_columns = []
    dimension_columns = []
    date_columns = []

    for column in dataframe.columns:

        series = dataframe[column]

        # ----------------------------------------------------
        # NUMERIC COLUMNS
        # ----------------------------------------------------

        numeric_series = pd.to_numeric(
            series,
            errors="coerce",
        )

        numeric_valid_count = numeric_series.notna().sum()

        if numeric_valid_count > 0:
            numeric_columns.append(column)

        # ----------------------------------------------------
        # DATE COLUMNS
        #
        # IMPORTANT:
        # Do not allow numeric columns to become date columns.
        # ----------------------------------------------------

        is_numeric_dtype = pd.api.types.is_numeric_dtype(
            series
        )

        if not is_numeric_dtype:

            date_series = pd.to_datetime(
                series,
                errors="coerce",
            )

            date_valid_count = date_series.notna().sum()

            total_non_null = series.notna().sum()

            if total_non_null > 0:

                date_valid_ratio = (
                    date_valid_count / total_non_null
                )

                # Require at least 70% of non-null values
                # to be valid dates.
                if date_valid_ratio >= 0.70:
                    date_columns.append(column)

        # ----------------------------------------------------
        # DIMENSION COLUMNS
        # ----------------------------------------------------

        if (
            series.dtype == "object"
            or str(series.dtype).startswith("category")
            or pd.api.types.is_string_dtype(series)
        ):
            dimension_columns.append(column)

    # --------------------------------------------------------
    # REMOVE DATE COLUMNS FROM DIMENSIONS
    # --------------------------------------------------------

    dimension_columns = [
        column
        for column in dimension_columns
        if column not in date_columns
    ]

    # --------------------------------------------------------
    # SELECTED FORM VALUES
    #
    # GET values are used when the page is refreshed after
    # changing dataset/version/date column.
    #
    # POST values are used when analysis has been submitted.
    # --------------------------------------------------------

    selected_metric_column = (
        request.POST.get(
            "metric_column",
            "",
        ).strip()
        if request.method == "POST"
        else request.GET.get(
            "metric_column",
            "",
        ).strip()
    )

    selected_dimension_column = (
        request.POST.get(
            "dimension_column",
            "",
        ).strip()
        if request.method == "POST"
        else request.GET.get(
            "dimension_column",
            "",
        ).strip()
    )

    selected_date_column = (
        request.POST.get(
            "date_column",
            "",
        ).strip()
        if request.method == "POST"
        else request.GET.get(
            "date_column",
            "",
        ).strip()
    )

    selected_target_period = (
        request.POST.get(
            "target_period",
            "",
        ).strip()
        if request.method == "POST"
        else request.GET.get(
            "target_period",
            "",
        ).strip()
    )

    selected_comparison_period = (
        request.POST.get(
            "comparison_period",
            "",
        ).strip()
        if request.method == "POST"
        else request.GET.get(
            "comparison_period",
            "",
        ).strip()
    )

    # --------------------------------------------------------
    # VALIDATE DATE COLUMN
    # --------------------------------------------------------

    if selected_date_column not in date_columns:
        selected_date_column = ""

    # --------------------------------------------------------
    # AVAILABLE PERIODS
    #
    # Generate months from the selected dataset/version
    # and selected date column.
    # --------------------------------------------------------

    available_periods = []

    if selected_date_column:

        try:

            parsed_dates = pd.to_datetime(
                dataframe[selected_date_column],
                errors="coerce",
            )

            periods = (
                parsed_dates
                .dropna()
                .dt.to_period("M")
                .drop_duplicates()
                .sort_values()
            )

            available_periods = [
                {
                    "value": str(period),
                    "label": period.strftime("%B %Y"),
                }
                for period in periods
            ]

        except Exception:
            available_periods = []

    # --------------------------------------------------------
    # If the selected date column is empty, do not allow
    # stale period values from another dataset/version.
    # --------------------------------------------------------

    available_period_values = {
        period["value"]
        for period in available_periods
    }

    if (
        selected_target_period
        and selected_target_period not in available_period_values
    ):
        selected_target_period = ""

    if (
        selected_comparison_period
        and selected_comparison_period not in available_period_values
    ):
        selected_comparison_period = ""

    # --------------------------------------------------------
    # POST - RUN ANALYSIS
    # --------------------------------------------------------

    if request.method == "POST":

        metric_column = request.POST.get(
            "metric_column",
            "",
        ).strip()

        dimension_column = request.POST.get(
            "dimension_column",
            "",
        ).strip()

        date_column = request.POST.get(
            "date_column",
            "",
        ).strip()

        target_period = request.POST.get(
            "target_period",
            "",
        ).strip()

        comparison_period = request.POST.get(
            "comparison_period",
            "",
        ).strip()

        # ----------------------------------------------------
        # VALIDATE METRIC
        # ----------------------------------------------------

        if not metric_column:

            messages.error(
                request,
                "Please select a metric column.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                        "metric_column": metric_column,
                        "dimension_column": dimension_column,
                        "date_column": date_column,
                        "target_period": target_period,
                        "comparison_period": comparison_period,
                    }
                )
            )

        if metric_column not in numeric_columns:

            messages.error(
                request,
                "The selected metric column is not valid for this dataset.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        # ----------------------------------------------------
        # VALIDATE DIMENSION
        # ----------------------------------------------------

        if not dimension_column:

            messages.error(
                request,
                "Please select a dimension column.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                        "metric_column": metric_column,
                        "dimension_column": dimension_column,
                        "date_column": date_column,
                    }
                )
            )

        if dimension_column not in dimension_columns:

            messages.error(
                request,
                "The selected dimension column is not valid for this dataset.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        # ----------------------------------------------------
        # DATE COLUMN
        # ----------------------------------------------------

        if not date_column:
            date_column = None

        elif date_column not in date_columns:

            messages.error(
                request,
                "The selected date column is not valid for this dataset.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        # ----------------------------------------------------
        # PERIOD VALIDATION
        # ----------------------------------------------------

        if date_column:

            if not target_period:

                messages.error(
                    request,
                    "Please select a target period.",
                )

                return redirect(
                    request.path
                    + "?"
                    + urlencode(
                        {
                            "dataset": selected_dataset.id,
                            "version": selected_version.id,
                            "metric_column": metric_column,
                            "dimension_column": dimension_column,
                            "date_column": date_column,
                        }
                    )
                )

            if not comparison_period:

                messages.error(
                    request,
                    "Please select a comparison period.",
                )

                return redirect(
                    request.path
                    + "?"
                    + urlencode(
                        {
                            "dataset": selected_dataset.id,
                            "version": selected_version.id,
                            "metric_column": metric_column,
                            "dimension_column": dimension_column,
                            "date_column": date_column,
                            "target_period": target_period,
                        }
                    )
                )

            if target_period not in available_period_values:

                messages.error(
                    request,
                    "The selected target period is not available in the dataset.",
                )

                return redirect(
                    request.path
                    + "?"
                    + urlencode(
                        {
                            "dataset": selected_dataset.id,
                            "version": selected_version.id,
                            "metric_column": metric_column,
                            "dimension_column": dimension_column,
                            "date_column": date_column,
                        }
                    )
                )

            if comparison_period not in available_period_values:

                messages.error(
                    request,
                    "The selected comparison period is not available in the dataset.",
                )

                return redirect(
                    request.path
                    + "?"
                    + urlencode(
                        {
                            "dataset": selected_dataset.id,
                            "version": selected_version.id,
                            "metric_column": metric_column,
                            "dimension_column": dimension_column,
                            "date_column": date_column,
                            "target_period": target_period,
                        }
                    )
                )

            if target_period == comparison_period:

                messages.error(
                    request,
                    "Target Period and Comparison Period must be different.",
                )

                return redirect(
                    request.path
                    + "?"
                    + urlencode(
                        {
                            "dataset": selected_dataset.id,
                            "version": selected_version.id,
                            "metric_column": metric_column,
                            "dimension_column": dimension_column,
                            "date_column": date_column,
                        }
                    )
                )

        else:

            target_period = ""
            comparison_period = ""

        # ----------------------------------------------------
        # CREATE INSIGHT RUN
        # ----------------------------------------------------

        insight_run = InsightRun.objects.create(
            dataset=selected_dataset,
            dataset_version=selected_version,
            insight_type="Root Cause Analysis",
            status="Running",
            parameters={
                "metric_column": metric_column,
                "dimension_column": dimension_column,
                "date_column": date_column or "",
                "target_period": target_period,
                "comparison_period": comparison_period,
            },
            created_by=request.user,
        )

        try:

            # ------------------------------------------------
            # RUN ROOT CAUSE ANALYSIS
            # ------------------------------------------------

            result = analyze_root_causes(
                dataframe=dataframe,
                metric_column=metric_column,
                dimension_column=dimension_column,
                date_column=date_column,
                target_period=target_period or None,
                comparison_period=comparison_period or None,
            )

            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            RootCauseResult.objects.create(
                insight_run=insight_run,

                metric_column=result[
                    "metric_column"
                ],

                date_column=result[
                    "date_column"
                ],

                dimension_column=result[
                    "dimension_column"
                ],

                analysis_type=result[
                    "analysis_type"
                ],

                target_period=result[
                    "target_period"
                ],

                comparison_period=result[
                    "comparison_period"
                ],

                total_value=result[
                    "total_value"
                ],

                comparison_value=result[
                    "comparison_value"
                ],

                change_value=result[
                    "change_value"
                ],

                change_percentage=result[
                    "change_percentage"
                ],

                primary_cause=result[
                    "primary_cause"
                ],

                primary_cause_contribution=result[
                    "primary_cause_contribution"
                ],

                cause_count=result[
                    "cause_count"
                ],

                summary=result[
                    "summary"
                ],

                cause_data=result[
                    "cause_data"
                ],

                chart_data=result[
                    "chart_data"
                ],
            )

            # ------------------------------------------------
            # COMPLETE RUN
            # ------------------------------------------------

            insight_run.status = "Completed"
            insight_run.completed_at = timezone.now()

            insight_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            messages.success(
                request,
                "Root Cause Analysis completed successfully.",
            )

        except Exception as exc:

            insight_run.status = "Failed"
            insight_run.error_message = str(exc)
            insight_run.completed_at = timezone.now()

            insight_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            messages.error(
                request,
                f"Root Cause Analysis failed: {exc}",
            )

    # --------------------------------------------------------
    # LATEST COMPLETED RESULT
    # --------------------------------------------------------

    root_cause_result = (
        RootCauseResult.objects
        .filter(
            insight_run__created_by=request.user,
            insight_run__dataset=selected_dataset,
            insight_run__dataset_version=selected_version,
            insight_run__status="Completed",
        )
        .select_related("insight_run")
        .first()
    )

    # --------------------------------------------------------
    # PAGE CONTEXT
    # --------------------------------------------------------

    context = {
        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "versions": versions,

        "selected_version": selected_version,

        "numeric_columns": numeric_columns,

        "dimension_columns": dimension_columns,

        "date_columns": date_columns,

        "available_periods": available_periods,

        "selected_metric_column": selected_metric_column,

        "selected_dimension_column": selected_dimension_column,

        "selected_date_column": selected_date_column,

        "selected_target_period": selected_target_period,

        "selected_comparison_period": selected_comparison_period,

        "root_cause_result": root_cause_result,
    }

    return render(
        request,
        "advanced_insights/root_cause_analysis.html",
        context,
    )

# ============================================================
# CUSTOMER SEGMENTATION
# ============================================================

@login_required
def customer_segmentation(request):

    # --------------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # USER DATASETS
    # --------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if not datasets.exists():
        messages.warning(
            request,
            "Please upload a dataset before using Customer Segmentation.",
        )

        return render(
            request,
            "advanced_insights/customer_segmentation.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "versions": [],
                "selected_version": None,
                "customer_columns": [],
                "numeric_columns": [],
                "selected_customer_column": "",
                "selected_metric_columns": [],
                "selected_segments": 4,
                "segmentation_result": None,
            },
        )

    # --------------------------------------------------------
    # SELECT DATASET
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    selected_dataset = None

    if dataset_id:
        try:
            selected_dataset = datasets.get(
                id=dataset_id
            )
        except Dataset.DoesNotExist:
            selected_dataset = None

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # DATASET VERSIONS
    # --------------------------------------------------------

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    if not versions.exists():

        messages.warning(
            request,
            "The selected dataset does not have any versions.",
        )

        return render(
            request,
            "advanced_insights/customer_segmentation.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "versions": versions,
                "selected_version": None,
                "customer_columns": [],
                "numeric_columns": [],
                "selected_customer_column": "",
                "selected_metric_columns": [],
                "selected_segments": 4,
                "segmentation_result": None,
            },
        )

    # --------------------------------------------------------
    # SELECT VERSION
    # --------------------------------------------------------

    version_id = request.GET.get("version")

    selected_version = None

    if version_id:
        try:
            selected_version = versions.get(
                id=version_id
            )
        except DatasetVersion.DoesNotExist:
            selected_version = None

    if selected_version is None:
        selected_version = (
            versions
            .filter(is_current=True)
            .first()
        )

    if selected_version is None:
        selected_version = versions.first()

    # --------------------------------------------------------
    # READ CLEANED/VERSIONED DATA
    # --------------------------------------------------------

    try:
        dataframe = read_dataset_version_file(
            selected_version
        )

    except Exception as exc:

        messages.error(
            request,
            f"Unable to read the selected dataset version: {exc}",
        )

        return render(
            request,
            "advanced_insights/customer_segmentation.html",
            {
                "datasets": datasets,
                "selected_dataset": selected_dataset,
                "versions": versions,
                "selected_version": selected_version,
                "customer_columns": [],
                "numeric_columns": [],
                "selected_customer_column": "",
                "selected_metric_columns": [],
                "selected_segments": 4,
                "segmentation_result": None,
            },
        )

    # --------------------------------------------------------
    # DETECT CUSTOMER COLUMNS
    # --------------------------------------------------------

    customer_columns = []

    customer_aliases = [
        "customer",
        "customer_id",
        "customer id",
        "customerid",
        "customer_name",
        "customer name",
        "customer_number",
        "customer code",
        "client",
        "client_id",
        "buyer_id",
    ]

    normalized_aliases = {
        alias
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for alias in customer_aliases
    }

    for column in dataframe.columns:

        normalized_column = (
            str(column)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        if normalized_column in normalized_aliases:

            if column not in customer_columns:
                customer_columns.append(column)

    # Fallback: look for columns containing customer/client/buyer
    if not customer_columns:

        for column in dataframe.columns:

            normalized_column = (
                str(column)
                .strip()
                .lower()
            )

            if any(
                keyword in normalized_column
                for keyword in [
                    "customer",
                    "client",
                    "buyer",
                ]
            ):

                if column not in customer_columns:
                    customer_columns.append(column)

    # --------------------------------------------------------
    # DETECT NUMERIC COLUMNS
    # --------------------------------------------------------

    numeric_columns = []

    for column in dataframe.columns:

        numeric_series = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        if numeric_series.notna().sum() > 0:
            numeric_columns.append(column)

    # --------------------------------------------------------
    # SELECTED VALUES
    # --------------------------------------------------------

    selected_customer_column = (
        request.GET.get(
            "customer_column",
            ""
        ).strip()
    )

    if (
        selected_customer_column
        not in customer_columns
    ):
        selected_customer_column = (
            customer_columns[0]
            if customer_columns
            else ""
        )

    selected_metric_columns = [
        column
        for column in request.GET.getlist(
            "metric_columns"
        )
        if column in numeric_columns
    ]

    # --------------------------------------------------------
    # DEFAULT METRICS
    # --------------------------------------------------------

    if not selected_metric_columns:

        preferred_metrics = [
            "Sales_Amount",
            "Sales Amount",
            "Revenue",
            "Sales",
            "Amount",
            "Quantity",
            "Profit",
        ]

        for preferred in preferred_metrics:

            for column in numeric_columns:

                if str(column).strip().lower() == (
                    preferred.strip().lower()
                ):

                    if column not in selected_metric_columns:
                        selected_metric_columns.append(
                            column
                        )

        # If no preferred metrics were found,
        # use the first available numeric columns.
        if not selected_metric_columns:

            selected_metric_columns = (
                numeric_columns[:3]
            )

    # --------------------------------------------------------
    # NUMBER OF SEGMENTS
    # --------------------------------------------------------

    selected_segments = request.GET.get(
        "segments",
        "4",
    )

    try:
        selected_segments = int(
            selected_segments
        )
    except (TypeError, ValueError):
        selected_segments = 4

    selected_segments = max(
        2,
        min(selected_segments, 5),
    )

    # --------------------------------------------------------
    # POST — RUN ANALYSIS
    # --------------------------------------------------------

    if request.method == "POST":

        customer_column = (
            request.POST
            .get(
                "customer_column",
                "",
            )
            .strip()
        )

        metric_columns = [
            column
            for column in request.POST.getlist(
                "metric_columns"
            )
            if column in numeric_columns
        ]

        segments_value = request.POST.get(
            "segments",
            "4",
        )

        try:
            number_of_segments = int(
                segments_value
            )
        except (TypeError, ValueError):
            number_of_segments = 4

        number_of_segments = max(
            2,
            min(number_of_segments, 5),
        )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not customer_column:

            messages.error(
                request,
                "Please select a customer column.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        if customer_column not in customer_columns:

            messages.error(
                request,
                "The selected customer column is not valid.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        if not metric_columns:

            messages.error(
                request,
                "Please select at least one numerical metric.",
            )

            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                    }
                )
            )

        # ----------------------------------------------------
        # CREATE INSIGHT RUN
        # ----------------------------------------------------

        insight_run = InsightRun.objects.create(
            dataset=selected_dataset,
            dataset_version=selected_version,
            insight_type="Customer Segmentation",
            status="Running",
            parameters={
                "customer_column": customer_column,
                "metric_columns": metric_columns,
                "number_of_segments": (
                    number_of_segments
                ),
            },
            created_by=request.user,
        )

        # ----------------------------------------------------
        # RUN ANALYSIS
        # ----------------------------------------------------

        try:

            result = analyze_customer_segments(
                dataframe=dataframe,
                customer_column=customer_column,
                metric_columns=metric_columns,
                number_of_segments=(
                    number_of_segments
                ),
            )

            # ------------------------------------------------
            # SAVE RESULT
            # ------------------------------------------------

            CustomerSegmentationResult.objects.create(
                insight_run=insight_run,

                customer_column=(
                    result["customer_column"]
                ),

                metric_columns=(
                    result["metric_columns"]
                ),

                segmentation_method=(
                    result["segmentation_method"]
                ),

                number_of_segments=(
                    result["number_of_segments"]
                ),

                total_records=(
                    result["total_records"]
                ),

                total_customers=(
                    result["total_customers"]
                ),

                segmented_customers=(
                    result["segmented_customers"]
                ),

                segment_count=(
                    result["segment_count"]
                ),

                largest_segment=(
                    result["largest_segment"]
                ),

                largest_segment_count=(
                    result["largest_segment_count"]
                ),

                summary=(
                    result["summary"]
                ),

                segment_data=(
                    result["segment_data"]
                ),

                customer_data=(
                    result["customer_data"]
                ),

                chart_data=(
                    result["chart_data"]
                ),
            )

            # ------------------------------------------------
            # COMPLETE RUN
            # ------------------------------------------------

            insight_run.status = "Completed"

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "completed_at",
                ]
            )

            messages.success(
                request,
                "Customer Segmentation completed successfully.",
            )

            # Keep the selected configuration
            # visible after the POST.
            return redirect(
                request.path
                + "?"
                + urlencode(
                    {
                        "dataset": selected_dataset.id,
                        "version": selected_version.id,
                        "customer_column": customer_column,
                        "segments": number_of_segments,
                    }
                )
            )

        except Exception as exc:

            insight_run.status = "Failed"

            insight_run.error_message = str(
                exc
            )

            insight_run.completed_at = (
                timezone.now()
            )

            insight_run.save(
                update_fields=[
                    "status",
                    "error_message",
                    "completed_at",
                ]
            )

            messages.error(
                request,
                f"Customer Segmentation failed: {exc}",
            )

    # --------------------------------------------------------
    # LOAD LATEST COMPLETED RESULT
    # --------------------------------------------------------

    segmentation_result = (
        CustomerSegmentationResult.objects
        .filter(
            insight_run__created_by=request.user,
            insight_run__dataset=selected_dataset,
            insight_run__dataset_version=selected_version,
            insight_run__status="Completed",
        )
        .select_related(
            "insight_run"
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "versions": versions,

        "selected_version": (
            selected_version
        ),

        "customer_columns": (
            customer_columns
        ),

        "numeric_columns": (
            numeric_columns
        ),

        "selected_customer_column": (
            selected_customer_column
        ),

        "selected_metric_columns": (
            selected_metric_columns
        ),

        "selected_segments": (
            selected_segments
        ),

        "segmentation_result": (
            segmentation_result
        ),
    }

    return render(
        request,
        "advanced_insights/customer_segmentation.html",
        context,
    )
@login_required
def churn_risk_analysis(request):
    # ========================================================
    # APPROVAL CHECK
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
    # DATASETS
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if not datasets.exists():
        messages.warning(
            request,
            "Please upload a dataset before running Churn / Risk Analysis.",
        )

        return render(
            request,
            "advanced_insights/churn_risk_analysis.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "versions": [],
                "selected_version": None,
                "customer_columns": [],
                "date_columns": [],
                "numeric_columns": [],
                "selected_customer_column": "",
                "selected_date_column": "",
                "selected_metric_columns": [],
                "churn_result": None,
            },
        )

    # ========================================================
    # SELECT DATASET
    # ========================================================

    dataset_id = request.GET.get("dataset")

    selected_dataset = (
        datasets.filter(id=dataset_id).first()
        if dataset_id
        else datasets.first()
    )

    if not selected_dataset:
        selected_dataset = datasets.first()

    # ========================================================
    # DATASET VERSIONS
    # ========================================================

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    version_id = request.GET.get("version")

    selected_version = (
        versions.filter(id=version_id).first()
        if version_id
        else None
    )

    if not selected_version:
        selected_version = (
            versions
            .filter(is_current=True)
            .first()
        )

    if not selected_version:
        selected_version = versions.first()

    # ========================================================
    # BASIC CONTEXT
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "customer_columns": [],
        "date_columns": [],
        "numeric_columns": [],
        "selected_customer_column": "",
        "selected_date_column": "",
        "selected_metric_columns": [],
        "churn_result": None,
    }

    if not selected_version:
        messages.warning(
            request,
            "The selected dataset does not contain a usable data version.",
        )

        return render(
            request,
            "advanced_insights/churn_risk_analysis.html",
            context,
        )

    # ========================================================
    # READ CURRENT DATA VERSION
    # ========================================================

    try:
        dataframe = read_dataset_version_file(
            selected_version
        )

    except Exception as exc:
        messages.error(
            request,
            f"Unable to read the selected dataset version: {exc}",
        )

        return render(
            request,
            "advanced_insights/churn_risk_analysis.html",
            context,
        )

    if dataframe is None or dataframe.empty:
        messages.warning(
            request,
            "The selected dataset version contains no usable records.",
        )

        return render(
            request,
            "advanced_insights/churn_risk_analysis.html",
            context,
        )

    # ========================================================
    # DETECT CUSTOMER COLUMN
    # ========================================================

    customer_columns = []

    customer_aliases = [
        "Customer_ID",
        "Customer ID",
        "CustomerID",
        "customer_id",
        "customer",
        "customer_name",
        "customer_number",
        "customer_code",
        "client_id",
        "client",
        "buyer_id",
        "buyer",
        "account_id",
        "account",
    ]

    normalized_customer_aliases = {
        str(alias)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        for alias in customer_aliases
    }

    for column in dataframe.columns:

        normalized_column = (
            str(column)
            .strip()
            .lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

        if normalized_column in normalized_customer_aliases:
            customer_columns.append(column)

    # ========================================================
    # FALLBACK CUSTOMER DETECTION
    # ========================================================

    if not customer_columns:

        for column in dataframe.columns:

            normalized_column = (
                str(column)
                .strip()
                .lower()
            )

            if (
                "customer" in normalized_column
                or "client" in normalized_column
                or "buyer" in normalized_column
            ):
                customer_columns.append(column)

    # ========================================================
    # DETECT DATE COLUMNS
    # ========================================================

    date_columns = []

    for column in dataframe.columns:

        series = dataframe[column]

        if pd.api.types.is_numeric_dtype(series):
            continue

        parsed = pd.to_datetime(
            series,
            errors="coerce",
        )

        non_empty = series.notna().sum()

        if non_empty == 0:
            continue

        success_rate = (
            parsed.notna().sum()
            / non_empty
        )

        if success_rate >= 0.70:
            date_columns.append(column)

    # ========================================================
    # DETECT NUMERIC COLUMNS
    # ========================================================

    numeric_columns = []

    for column in dataframe.columns:

        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        if numeric_values.notna().sum() > 0:
            numeric_columns.append(column)

    # ========================================================
    # SELECT DEFAULT CUSTOMER COLUMN
    # ========================================================

    selected_customer_column = (
        request.GET.get("customer_column")
        or (
            customer_columns[0]
            if customer_columns
            else ""
        )
    )

    # ========================================================
    # SELECT DEFAULT DATE COLUMN
    # ========================================================

    selected_date_column = (
        request.GET.get("date_column")
        or (
            detect_date_column(dataframe)
            or ""
        )
    )

    # ========================================================
    # SELECT METRIC COLUMNS
    # ========================================================

    # IMPORTANT:
    # getlist() is required because metric_columns can
    # contain multiple selected values.

    selected_metric_columns = request.GET.getlist(
        "metric_columns"
    )

    # Only use automatic detection when there are
    # genuinely no metrics in the URL.

    if not selected_metric_columns:

        detected_metrics = detect_activity_metrics(
            dataframe
        )

        selected_metric_columns = [
            column
            for column in detected_metrics
            if column in numeric_columns
        ][:4]

    # ========================================================
    # POST — RUN CHURN / RISK ANALYSIS
    # ========================================================

    if request.method == "POST":

        selected_customer_column = (
            request.POST.get(
                "customer_column"
            )
            or selected_customer_column
        )

        selected_date_column = (
            request.POST.get(
                "date_column"
            )
            or selected_date_column
        )

        # IMPORTANT:
        # This retrieves ALL checked metric checkboxes.

        selected_metric_columns = (
            request.POST.getlist(
                "metric_columns"
            )
        )

        # Empty date selection is allowed.

        if selected_date_column == "":
            selected_date_column = None

        # ----------------------------------------------------
        # VALIDATE METRIC SELECTION
        # ----------------------------------------------------

        # If your design requires at least one metric,
        # prevent the analysis from running without one.

        if not selected_metric_columns:
            messages.error(
                request,
                "Please select at least one activity or value metric.",
            )

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        elif not selected_customer_column:

            messages.error(
                request,
                "Please select a customer column.",
            )

        elif selected_customer_column not in dataframe.columns:

            messages.error(
                request,
                "The selected customer column is not available.",
            )

        elif (
            selected_date_column
            and selected_date_column not in dataframe.columns
        ):

            messages.error(
                request,
                "The selected date column is not available.",
            )

        elif any(
            metric not in dataframe.columns
            for metric in selected_metric_columns
        ):

            messages.error(
                request,
                "One or more selected metrics are not available in the dataset.",
            )

        else:

            try:

                # --------------------------------------------
                # CREATE INSIGHT RUN
                # --------------------------------------------

                insight_run = InsightRun.objects.create(
                    dataset=selected_dataset,
                    dataset_version=selected_version,
                    insight_type="Churn Risk",
                    status="Running",
                    parameters={
                        "customer_column": (
                            selected_customer_column
                        ),
                        "date_column": (
                            selected_date_column
                            or ""
                        ),
                        "metric_columns": (
                            selected_metric_columns
                        ),
                    },
                    created_by=request.user,
                )

                # --------------------------------------------
                # ANALYZE
                # --------------------------------------------

                result = analyze_churn_risk(
                    dataframe=dataframe,
                    customer_column=(
                        selected_customer_column
                    ),
                    date_column=(
                        selected_date_column
                    ),
                    metric_columns=(
                        selected_metric_columns
                    ),
                )

                # --------------------------------------------
                # SAVE RESULT
                # --------------------------------------------

                ChurnRiskResult.objects.create(
                    insight_run=insight_run,

                    customer_column=(
                        result[
                            "customer_column"
                        ]
                    ),

                    date_column=(
                        result[
                            "date_column"
                        ]
                    ),

                    metric_columns=(
                        result[
                            "metric_columns"
                        ]
                    ),

                    risk_method=(
                        result[
                            "risk_method"
                        ]
                    ),

                    total_records=(
                        result[
                            "total_records"
                        ]
                    ),

                    total_customers=(
                        result[
                            "total_customers"
                        ]
                    ),

                    assessed_customers=(
                        result[
                            "assessed_customers"
                        ]
                    ),

                    high_risk_customers=(
                        result[
                            "high_risk_customers"
                        ]
                    ),

                    medium_risk_customers=(
                        result[
                            "medium_risk_customers"
                        ]
                    ),

                    low_risk_customers=(
                        result[
                            "low_risk_customers"
                        ]
                    ),

                    high_risk_percentage=(
                        result[
                            "high_risk_percentage"
                        ]
                    ),

                    average_risk_score=(
                        result[
                            "average_risk_score"
                        ]
                    ),

                    highest_risk_customer=(
                        result[
                            "highest_risk_customer"
                        ]
                    ),

                    highest_risk_score=(
                        result[
                            "highest_risk_score"
                        ]
                    ),

                    summary=(
                        result[
                            "summary"
                        ]
                    ),

                    risk_data=(
                        result[
                            "risk_data"
                        ]
                    ),

                    customer_data=(
                        result[
                            "customer_data"
                        ]
                    ),

                    chart_data=(
                        result[
                            "chart_data"
                        ]
                    ),
                )

                # --------------------------------------------
                # COMPLETE RUN
                # --------------------------------------------

                insight_run.status = "Completed"
                insight_run.completed_at = timezone.now()

                insight_run.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                messages.success(
                    request,
                    "Churn / Risk Analysis completed successfully.",
                )

                # --------------------------------------------
                # REDIRECT
                # --------------------------------------------

                # IMPORTANT:
                # Preserve every selected metric in the
                # query string so the checkboxes remain
                # selected after the page reloads.

                query_data = [
                    (
                        "dataset",
                        selected_dataset.id,
                    ),
                    (
                        "version",
                        selected_version.id,
                    ),
                    (
                        "customer_column",
                        selected_customer_column,
                    ),
                    (
                        "date_column",
                        selected_date_column or "",
                    ),
                ]

                # Add every selected metric separately.
                #
                # Example:
                # ?metric_columns=PurchaseAmount
                # &metric_columns=Profit

                for metric in selected_metric_columns:
                    query_data.append(
                        (
                            "metric_columns",
                            metric,
                        )
                    )

                query = urlencode(
                    query_data,
                    doseq=True,
                )

                return redirect(
                    f"{request.path}?{query}"
                )

            except Exception as exc:

                if "insight_run" in locals():

                    insight_run.status = "Failed"
                    insight_run.error_message = str(exc)
                    insight_run.completed_at = timezone.now()

                    insight_run.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "completed_at",
                        ]
                    )

                messages.error(
                    request,
                    f"Churn / Risk Analysis failed: {exc}",
                )

    # ========================================================
    # LOAD LATEST COMPLETED RESULT
    # ========================================================

    churn_result = (
        ChurnRiskResult.objects
        .filter(
            insight_run__created_by=request.user,
            insight_run__dataset=selected_dataset,
            insight_run__dataset_version=selected_version,
            insight_run__status="Completed",
        )
        .select_related("insight_run")
        .order_by("-created_at")
        .first()
    )

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context.update(
        {
            "customer_columns": customer_columns,
            "date_columns": date_columns,
            "numeric_columns": numeric_columns,

            "selected_customer_column": (
                selected_customer_column
            ),

            "selected_date_column": (
                selected_date_column or ""
            ),

            "selected_metric_columns": (
                selected_metric_columns
            ),

            "churn_result": churn_result,
        }
    )

    return render(
        request,
        "advanced_insights/churn_risk_analysis.html",
        context,
    )

# ============================================================
# OPPORTUNITY DETECTION
# ============================================================

@login_required
def opportunity_detection(request):

    # ========================================================
    # APPROVAL CHECK
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
    # DATASETS
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True,
        )
        .order_by("-uploaded_at")
    )

    if not datasets.exists():

        messages.warning(
            request,
            "Please upload a dataset before running "
            "Opportunity Detection.",
        )

        return render(
            request,
            "advanced_insights/opportunity_detection.html",
            {
                "datasets": datasets,
                "selected_dataset": None,
                "versions": [],
                "selected_version": None,
                "dimension_columns": [],
                "value_columns": [],
                "date_columns": [],
                "selected_dimension_column": "",
                "selected_value_column": "",
                "selected_date_column": "",
                "opportunity_result": None,
            },
        )

    # ========================================================
    # SELECT DATASET
    # ========================================================

    dataset_id = request.GET.get("dataset")

    selected_dataset = (
        datasets.filter(id=dataset_id).first()
        if dataset_id
        else datasets.first()
    )

    if not selected_dataset:
        selected_dataset = datasets.first()

    # ========================================================
    # DATASET VERSIONS
    # ========================================================

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=selected_dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )

    version_id = request.GET.get("version")

    selected_version = (
        versions.filter(id=version_id).first()
        if version_id
        else None
    )

    if not selected_version:

        selected_version = (
            versions
            .filter(is_current=True)
            .first()
        )

    if not selected_version:
        selected_version = versions.first()

    # ========================================================
    # BASIC CONTEXT
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,

        "dimension_columns": [],
        "value_columns": [],
        "date_columns": [],

        "selected_dimension_column": "",
        "selected_value_column": "",
        "selected_date_column": "",

        "opportunity_result": None,
    }

    # ========================================================
    # NO VERSION
    # ========================================================

    if not selected_version:

        messages.warning(
            request,
            "The selected dataset does not contain "
            "a usable data version.",
        )

        return render(
            request,
            "advanced_insights/opportunity_detection.html",
            context,
        )

    # ========================================================
    # READ SELECTED DATA VERSION
    # ========================================================

    try:

        dataframe = read_dataset_version_file(
            selected_version
        )

    except Exception as exc:

        messages.error(
            request,
            f"Unable to read the selected dataset version: {exc}",
        )

        return render(
            request,
            "advanced_insights/opportunity_detection.html",
            context,
        )

    # ========================================================
    # EMPTY DATAFRAME
    # ========================================================

    if dataframe is None or dataframe.empty:

        messages.warning(
            request,
            "The selected dataset version contains "
            "no usable records.",
        )

        return render(
            request,
            "advanced_insights/opportunity_detection.html",
            context,
        )

    # ========================================================
    # DETECT COLUMNS
    # ========================================================

    dimension_columns = []
    value_columns = []
    date_columns = []

    # --------------------------------------------------------
    # DATE COLUMNS
    # --------------------------------------------------------

    for column in dataframe.columns:

        series = dataframe[column]

        # Numeric columns are not treated as dates.
        if pd.api.types.is_numeric_dtype(series):
            continue

        parsed = pd.to_datetime(
            series,
            errors="coerce",
        )

        non_empty = series.notna().sum()

        if non_empty == 0:
            continue

        success_rate = (
            parsed.notna().sum()
            / non_empty
        )

        if success_rate >= 0.70:
            date_columns.append(column)

    # --------------------------------------------------------
    # VALUE COLUMNS
    # --------------------------------------------------------

    for column in dataframe.columns:

        numeric_values = pd.to_numeric(
            dataframe[column],
            errors="coerce",
        )

        valid_numeric_count = (
            numeric_values.notna().sum()
        )

        if valid_numeric_count > 0:
            value_columns.append(column)

    # --------------------------------------------------------
    # DIMENSION COLUMNS
    # --------------------------------------------------------

    for column in dataframe.columns:

        # Date columns are not useful as dimensions
        # for this analysis.
        if column in date_columns:
            continue

        # Numeric columns are treated as value metrics.
        if column in value_columns:
            continue

        series = dataframe[column]

        if series.nunique(
            dropna=True
        ) <= 1:
            continue

        dimension_columns.append(column)

    # ========================================================
    # FALLBACK DIMENSION DETECTION
    # ========================================================

    # If there are no object/categorical columns,
    # use columns with a reasonable number of unique values.

    if not dimension_columns:

        for column in dataframe.columns:

            if column in date_columns:
                continue

            if column in value_columns:
                continue

            unique_count = dataframe[
                column
            ].nunique(
                dropna=True
            )

            if unique_count > 1:
                dimension_columns.append(
                    column
                )

    # ========================================================
    # DEFAULT DIMENSION
    # ========================================================

    selected_dimension_column = (
        request.GET.get(
            "dimension_column"
        )
        or (
            dimension_columns[0]
            if dimension_columns
            else ""
        )
    )

    # ========================================================
    # DEFAULT VALUE COLUMN
    # ========================================================

    selected_value_column = (
        request.GET.get(
            "value_column"
        )
        or (
            value_columns[0]
            if value_columns
            else ""
        )
    )

    # ========================================================
    # DEFAULT DATE COLUMN
    # ========================================================

    selected_date_column = (
        request.GET.get(
            "date_column"
        )
        or ""
    )

    # Try to use the first detected date only when
    # the user has not explicitly selected a date.

    if not selected_date_column and date_columns:

        selected_date_column = date_columns[0]

    # ========================================================
    # POST — RUN OPPORTUNITY DETECTION
    # ========================================================

    if request.method == "POST":

        # ----------------------------------------------------
        # READ USER SELECTIONS
        # ----------------------------------------------------

        selected_dimension_column = (
            request.POST.get(
                "dimension_column"
            )
            or selected_dimension_column
        )

        selected_value_column = (
            request.POST.get(
                "value_column"
            )
            or selected_value_column
        )

        selected_date_column = (
            request.POST.get(
                "date_column"
            )
            or ""
        )

        # ----------------------------------------------------
        # EMPTY DATE IS ALLOWED
        # ----------------------------------------------------

        if selected_date_column == "":
            selected_date_column = None

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not selected_dimension_column:

            messages.error(
                request,
                "Please select a dimension column.",
            )

        elif (
            selected_dimension_column
            not in dataframe.columns
        ):

            messages.error(
                request,
                "The selected dimension column "
                "is not available.",
            )

        elif not selected_value_column:

            messages.error(
                request,
                "Please select a value metric.",
            )

        elif (
            selected_value_column
            not in dataframe.columns
        ):

            messages.error(
                request,
                "The selected value metric "
                "is not available.",
            )

        elif (
            selected_date_column
            and selected_date_column
            not in dataframe.columns
        ):

            messages.error(
                request,
                "The selected date column "
                "is not available.",
            )

        else:

            # =================================================
            # RUN ANALYSIS
            # =================================================

            insight_run = None

            try:

                # ---------------------------------------------
                # CREATE INSIGHT RUN
                # ---------------------------------------------

                insight_run = InsightRun.objects.create(
                    dataset=selected_dataset,
                    dataset_version=selected_version,
                    insight_type="Opportunity Detection",
                    status="Running",

                    parameters={
                        "dimension_column": (
                            selected_dimension_column
                        ),
                        "value_column": (
                            selected_value_column
                        ),
                        "date_column": (
                            selected_date_column
                            or ""
                        ),
                    },

                    created_by=request.user,
                )

                # ---------------------------------------------
                # ANALYZE
                # ---------------------------------------------

                result = (
                    analyze_opportunity_detection(
                        dataframe=dataframe,

                        dimension_column=(
                            selected_dimension_column
                        ),

                        value_column=(
                            selected_value_column
                        ),

                        date_column=(
                            selected_date_column
                        ),
                    )
                )

                # ---------------------------------------------
                # SAVE RESULT
                # ---------------------------------------------

                OpportunityDetectionResult.objects.create(

                    insight_run=insight_run,

                    dimension_column=(
                        result[
                            "dimension_column"
                        ]
                    ),

                    value_column=(
                        result[
                            "value_column"
                        ]
                    ),

                    date_column=(
                        result[
                            "date_column"
                        ]
                    ),

                    opportunity_method=(
                        result[
                            "opportunity_method"
                        ]
                    ),

                    total_records=(
                        result[
                            "total_records"
                        ]
                    ),

                    total_opportunities=(
                        result[
                            "total_opportunities"
                        ]
                    ),

                    high_opportunities=(
                        result[
                            "high_opportunities"
                        ]
                    ),

                    medium_opportunities=(
                        result[
                            "medium_opportunities"
                        ]
                    ),

                    low_opportunities=(
                        result[
                            "low_opportunities"
                        ]
                    ),

                    opportunity_percentage=(
                        result[
                            "opportunity_percentage"
                        ]
                    ),

                    average_opportunity_score=(
                        result[
                            "average_opportunity_score"
                        ]
                    ),

                    highest_opportunity=(
                        result[
                            "highest_opportunity"
                        ]
                    ),

                    highest_opportunity_score=(
                        result[
                            "highest_opportunity_score"
                        ]
                    ),

                    summary=(
                        result[
                            "summary"
                        ]
                    ),

                    opportunity_data=(
                        result[
                            "opportunity_data"
                        ]
                    ),

                    opportunity_details=(
                        result[
                            "opportunity_details"
                        ]
                    ),

                    chart_data=(
                        result[
                            "chart_data"
                        ]
                    ),
                )

                # ---------------------------------------------
                # COMPLETE RUN
                # ---------------------------------------------

                insight_run.status = "Completed"

                insight_run.completed_at = (
                    timezone.now()
                )

                insight_run.save(
                    update_fields=[
                        "status",
                        "completed_at",
                    ]
                )

                messages.success(
                    request,
                    "Opportunity Detection completed successfully.",
                )

                # ---------------------------------------------
                # REDIRECT
                # ---------------------------------------------

                query = urlencode(
                    {
                        "dataset": (
                            selected_dataset.id
                        ),

                        "version": (
                            selected_version.id
                        ),

                        "dimension_column": (
                            selected_dimension_column
                        ),

                        "value_column": (
                            selected_value_column
                        ),

                        "date_column": (
                            selected_date_column
                            or ""
                        ),
                    }
                )

                return redirect(
                    f"{request.path}?{query}"
                )

            except Exception as exc:

                # ---------------------------------------------
                # FAILED RUN
                # ---------------------------------------------

                if insight_run is not None:

                    insight_run.status = "Failed"

                    insight_run.error_message = str(
                        exc
                    )

                    insight_run.completed_at = (
                        timezone.now()
                    )

                    insight_run.save(
                        update_fields=[
                            "status",
                            "error_message",
                            "completed_at",
                        ]
                    )

                messages.error(
                    request,
                    f"Opportunity Detection failed: {exc}",
                )

    # ========================================================
    # LOAD LATEST COMPLETED RESULT
    # ========================================================

    opportunity_result = (
        OpportunityDetectionResult.objects
        .filter(
            insight_run__created_by=request.user,

            insight_run__dataset=(
                selected_dataset
            ),

            insight_run__dataset_version=(
                selected_version
            ),

            insight_run__status="Completed",
        )
        .select_related(
            "insight_run"
        )
        .order_by(
            "-created_at"
        )
        .first()
    )

    # ========================================================
    # FINAL CONTEXT
    # ========================================================

    context.update(
        {
            "dimension_columns": (
                dimension_columns
            ),

            "value_columns": (
                value_columns
            ),

            "date_columns": (
                date_columns
            ),

            "selected_dimension_column": (
                selected_dimension_column
            ),

            "selected_value_column": (
                selected_value_column
            ),

            "selected_date_column": (
                selected_date_column
                or ""
            ),

            "opportunity_result": (
                opportunity_result
            ),
        }
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "advanced_insights/opportunity_detection.html",
        context,
    )