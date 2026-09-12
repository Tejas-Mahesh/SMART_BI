import json
import pandas as pd

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from data_management.models import Dataset, DatasetVersion

from .services.forecasting import (
    detect_column,
    prepare_time_series,
    calculate_trend,
    forecast_series,
    calculate_forecast_summary,
)

from .services.anomaly_detection import (
    prepare_daily_series,
    detect_anomalies,
    calculate_anomaly_summary,
    generate_anomaly_insights,
)
from .services.root_cause import (
    detect_column as detect_root_column,
    prepare_data as prepare_root_data,
    calculate_periods,
    find_root_causes,
    generate_root_cause_insights,
)


from .services.customer_risk import (
    detect_column as detect_customer_column,
    run_customer_risk_analysis,
)
@login_required
def advanced_insights_dashboard(request):

    return render(
        request,
        "advanced_insights/dashboard.html",
    )


@login_required
def forecasting(request):

    datasets = (
        Dataset.objects
        .filter(owner=request.user)
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    historical_labels = []
    historical_values = []

    forecast_labels = []
    forecast_values = []

    total_historical = 0
    forecast_total = 0
    historical_average = 0
    forecast_average = 0

    forecast_change = 0

    trend_direction = "Unknown"
    forecast_direction = "Unknown"

    model_name = "Unavailable"
    confidence = "Low"

    date_column = ""
    metric_column = ""

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(id=dataset_id)
            .first()
        )

    else:

        selected_dataset = datasets.first()

    try:

        if not selected_dataset:

            raise ValueError(
                "No dataset is available. "
                "Upload a dataset from "
                "Data Management first."
            )

        # --------------------------------------
        # Find cleaned version
        # --------------------------------------

        selected_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Cleaned",
            )
            .order_by(
                "-version_number",
                "-created_at",
            )
            .first()
        )

        if not selected_version:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    is_current=True,
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

        if not selected_version:

            raise ValueError(
                "No cleaned dataset is available."
            )

        file_path = (
            selected_version.file.path
        )

        # --------------------------------------
        # Read dataset
        # --------------------------------------

        if file_path.lower().endswith(
            ".csv"
        ):

            df = pd.read_csv(
                file_path
            )

        elif file_path.lower().endswith(
            (".xlsx", ".xls")
        ):

            df = pd.read_excel(
                file_path
            )

        else:

            raise ValueError(
                "Unsupported dataset format."
            )

        if df.empty:

            raise ValueError(
                "The selected dataset is empty."
            )

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        # --------------------------------------
        # Detect date column
        # --------------------------------------

        date_column = detect_column(
            df,
            [
                "date",
                "order_date",
                "transaction_date",
                "sale_date",
                "created_at",
            ],
        )

        # --------------------------------------
        # Detect primary business metric
        # --------------------------------------

        metric_column = detect_column(
            df,
            [
                "sales",
                "revenue",
                "total_sales",
                "total_revenue",
                "net_sales",
                "amount",
                "order_value",
            ],
        )

        if not date_column:

            raise ValueError(
                "A date column could not be detected."
            )

        if not metric_column:

            raise ValueError(
                "A sales/revenue column could not "
                "be detected for forecasting."
            )

        # --------------------------------------
        # Build time series
        # --------------------------------------

        series = prepare_time_series(
            df,
            date_column,
            metric_column,
        )

        if series.empty:

            raise ValueError(
                "There is not enough valid "
                "time-series data."
            )

        # --------------------------------------
        # Historical values
        # --------------------------------------

        historical_labels = [
            date.strftime("%d %b %Y")
            for date in series.index
        ]

        historical_values = [
            round(float(value), 2)
            for value in series.values
        ]

        total_historical = float(
            series.sum()
        )

        # --------------------------------------
        # Trend
        # --------------------------------------

        trend = calculate_trend(
            series
        )

        trend_direction = (
            trend["direction"]
        )

        # --------------------------------------
        # Forecast
        # --------------------------------------

        forecast_result = forecast_series(
            series,
            periods=30,
        )

        forecast = (
            forecast_result["forecast"]
        )

        model_name = (
            forecast_result["model"]
        )

        confidence = (
            forecast_result["confidence"]
        )

        forecast_labels = [
            date.strftime("%d %b %Y")
            for date in forecast.index
        ]

        forecast_values = [
            round(float(value), 2)
            for value in forecast.values
        ]

        # --------------------------------------
        # Forecast summary
        # --------------------------------------

        summary = calculate_forecast_summary(
            series,
            forecast,
        )

        historical_average = (
            summary["historical_average"]
        )

        forecast_average = (
            summary["forecast_average"]
        )

        forecast_total = (
            summary["forecast_total"]
        )

        forecast_change = (
            summary["forecast_change"]
        )

        forecast_direction = (
            summary["forecast_direction"]
        )

        has_data = True

    except Exception as exc:

        error_message = str(exc)

    # ------------------------------------------
    # Business insights
    # ------------------------------------------

    insights = []

    if has_data:

        if trend_direction == "Increasing":

            insights.append(
                "Historical performance shows "
                "an increasing business trend."
            )

        elif trend_direction == "Decreasing":

            insights.append(
                "Historical performance shows "
                "a declining business trend."
            )

        else:

            insights.append(
                "Historical performance is "
                "relatively stable."
            )

        if forecast_direction == "Increasing":

            insights.append(
                f"The model forecasts approximately "
                f"{abs(forecast_change):.1f}% higher "
                "average daily performance over "
                "the next 30 days."
            )

        elif forecast_direction == "Decreasing":

            insights.append(
                f"The model forecasts approximately "
                f"{abs(forecast_change):.1f}% lower "
                "average daily performance over "
                "the next 30 days."
            )

        else:

            insights.append(
                "The forecast indicates relatively "
                "stable performance over the next "
                "30 days."
            )

        if confidence == "High":

            insights.append(
                "Forecast confidence is relatively "
                "high because sufficient historical "
                "observations are available."
            )

        elif confidence == "Medium":

            insights.append(
                "Forecast confidence is moderate. "
                "More historical data can improve "
                "future forecasting reliability."
            )

        else:

            insights.append(
                "Forecast confidence is low because "
                "the available historical period "
                "is limited."
            )

    context = {

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            selected_version,

        "has_data":
            has_data,

        "error_message":
            error_message,

        "historical_labels":
            json.dumps(
                historical_labels
            ),

        "historical_values":
            json.dumps(
                historical_values
            ),

        "forecast_labels":
            json.dumps(
                forecast_labels
            ),

        "forecast_values":
            json.dumps(
                forecast_values
            ),

        "total_historical":
            total_historical,

        "forecast_total":
            forecast_total,

        "historical_average":
            historical_average,

        "forecast_average":
            forecast_average,

        "forecast_change":
            forecast_change,

        "trend_direction":
            trend_direction,

        "forecast_direction":
            forecast_direction,

        "model_name":
            model_name,

        "confidence":
            confidence,

        "date_column":
            date_column,

        "metric_column":
            metric_column,

        "insights":
            insights,
    }

    return render(
        request,
        "advanced_insights/forecasting.html",
        context,
    )

@login_required
def anomaly_detection(request):

    datasets = Dataset.objects.filter(
    owner=request.user
).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    historical_labels = []
    historical_values = []

    anomaly_labels = []
    anomaly_values = []

    anomaly_points = []

    summary = {
        "total_days": 0,
        "anomaly_count": 0,
        "anomaly_rate": 0,
        "spike_count": 0,
        "drop_count": 0,
        "critical_count": 0,
        "largest_spike": 0,
        "largest_drop": 0,
        "largest_spike_date": None,
        "largest_drop_date": None,
    }

    insights = []

    date_column = None
    metric_column = None

    if datasets.exists():

        dataset_id = request.GET.get("dataset")

        if dataset_id:
            selected_dataset = datasets.filter(
                id=dataset_id
            ).first()

        if not selected_dataset:
            selected_dataset = datasets.first()

        if selected_dataset:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    version_type="Cleaned"
                )
                .order_by(
                    "-version_number",
                    "-created_at"
                )
                .first()
            )

            if not selected_version:

                selected_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=selected_dataset,
                        is_current=True
                    )
                    .order_by(
                        "-version_number",
                        "-created_at"
                    )
                    .first()
                )

            if selected_version:

                try:

                    file_path = selected_version.file.path

                    if file_path.lower().endswith(
                        (".xlsx", ".xls")
                    ):
                        df = pd.read_excel(file_path)

                    else:
                        df = pd.read_csv(file_path)

                    date_column = detect_column(
                        df,
                        [
                            "date",
                            "order_date",
                            "transaction_date",
                            "sale_date",
                            "created_at",
                            "invoice_date",
                        ]
                    )

                    metric_column = detect_column(
                        df,
                        [
                            "sales",
                            "sale",
                            "revenue",
                            "total_sales",
                            "total_revenue",
                            "net_sales",
                            "amount",
                            "order_value",
                        ]
                    )

                    if not date_column:

                        error_message = (
                            "A date column could not be detected "
                            "in this dataset."
                        )

                    elif not metric_column:

                        error_message = (
                            "A sales or revenue column could not "
                            "be detected in this dataset."
                        )

                    else:

                        series = prepare_daily_series(
                            df,
                            date_column,
                            metric_column
                        )

                        if series.empty:

                            error_message = (
                                "There is not enough valid date "
                                "and sales data for anomaly detection."
                            )

                        else:

                            anomaly_data = detect_anomalies(
                                series
                            )

                            summary = calculate_anomaly_summary(
                                series,
                                anomaly_data
                            )

                            insights = generate_anomaly_insights(
                                summary,
                                anomaly_data
                            )

                            has_data = True

                            # Historical chart
                            historical_labels = [
                                date.strftime("%Y-%m-%d")
                                for date in series.index
                            ]

                            historical_values = [
                                round(float(value), 2)
                                for value in series.values
                            ]

                            # Anomaly chart points
                            anomaly_rows = anomaly_data[
                                anomaly_data["is_anomaly"]
                            ]

                            anomaly_labels = [
                                row["date"].strftime("%Y-%m-%d")
                                for _, row in anomaly_rows.iterrows()
                            ]

                            anomaly_values = [
                                round(
                                    float(row["value"]),
                                    2
                                )
                                for _, row in anomaly_rows.iterrows()
                            ]

                            # Detailed anomaly table
                            for _, row in anomaly_rows.iterrows():

                                anomaly_points.append({
                                    "date": row["date"].strftime(
                                        "%Y-%m-%d"
                                    ),

                                    "value": round(
                                        float(row["value"]),
                                        2
                                    ),

                                    "expected": round(
                                        float(
                                            row["rolling_median"]
                                        ),
                                        2
                                    ),

                                    "deviation": round(
                                        float(
                                            row["deviation_percent"]
                                        ),
                                        2
                                    ),

                                    "direction": row[
                                        "direction"
                                    ],

                                    "severity": row[
                                        "severity"
                                    ],

                                    "impact": row[
                                        "impact"
                                    ],
                                })

                            # Most significant anomalies first
                            anomaly_points.sort(
                                key=lambda item: abs(
                                    item["deviation"]
                                ),
                                reverse=True
                            )

                except Exception as exc:

                    error_message = (
                        f"Unable to analyze this dataset: {exc}"
                    )

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "selected_version": selected_version,

        "has_data": has_data,
        "error_message": error_message,

        "historical_labels": json.dumps(
            historical_labels
        ),

        "historical_values": json.dumps(
            historical_values
        ),

        "anomaly_labels": json.dumps(
            anomaly_labels
        ),

        "anomaly_values": json.dumps(
            anomaly_values
        ),

        "anomaly_points": anomaly_points,

        "total_days": summary["total_days"],
        "anomaly_count": summary["anomaly_count"],
        "anomaly_rate": round(
            summary["anomaly_rate"],
            2
        ),

        "spike_count": summary["spike_count"],
        "drop_count": summary["drop_count"],
        "critical_count": summary["critical_count"],

        "largest_spike": round(
            summary["largest_spike"],
            2
        ),

        "largest_drop": round(
            summary["largest_drop"],
            2
        ),

        "largest_spike_date": summary[
            "largest_spike_date"
        ],

        "largest_drop_date": summary[
            "largest_drop_date"
        ],

        "date_column": date_column,
        "metric_column": metric_column,

        "insights": insights,
    }

    return render(
        request,
        "advanced_insights/anomaly_detection.html",
        context
    )

@login_required
def root_cause_analysis(request):

    datasets = Dataset.objects.filter(
        owner=request.user
    ).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    results = []
    insights = []

    total_current = 0
    total_previous = 0
    overall_change = 0

    current_start = None
    current_end = None
    previous_start = None
    previous_end = None

    date_column = None
    metric_column = None

    if datasets.exists():

        dataset_id = request.GET.get("dataset")

        if dataset_id:

            selected_dataset = datasets.filter(
                id=dataset_id
            ).first()

        if not selected_dataset:
            selected_dataset = datasets.first()

        if selected_dataset:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    version_type="Cleaned"
                )
                .order_by(
                    "-version_number",
                    "-created_at"
                )
                .first()
            )

            if not selected_version:

                selected_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=selected_dataset,
                        is_current=True
                    )
                    .order_by(
                        "-version_number",
                        "-created_at"
                    )
                    .first()
                )

            if selected_version:

                try:

                    file_path = selected_version.file.path

                    if file_path.lower().endswith(
                        (".xlsx", ".xls")
                    ):

                        df = pd.read_excel(
                            file_path
                        )

                    else:

                        df = pd.read_csv(
                            file_path
                        )

                    date_column = detect_root_column(
                        df,
                        [
                            "date",
                            "order_date",
                            "transaction_date",
                            "sale_date",
                            "created_at",
                            "invoice_date",
                        ]
                    )

                    metric_column = detect_root_column(
                        df,
                        [
                            "sales",
                            "sale",
                            "revenue",
                            "total_sales",
                            "total_revenue",
                            "net_sales",
                            "amount",
                            "order_value",
                        ]
                    )

                    if not date_column:

                        error_message = (
                            "A date column could not be detected "
                            "in this dataset."
                        )

                    elif not metric_column:

                        error_message = (
                            "A sales or revenue column could not "
                            "be detected in this dataset."
                        )

                    else:

                        data = prepare_root_data(
                            df,
                            date_column,
                            metric_column
                        )

                        if data.empty:

                            error_message = (
                                "There is not enough valid data "
                                "for root cause analysis."
                            )

                        else:

                            (
                                current,
                                previous,
                                current_start,
                                current_end,
                                previous_start,
                                previous_end,
                            ) = calculate_periods(
                                data,
                                date_column,
                                period_days=30
                            )

                            if current.empty:

                                error_message = (
                                    "The latest 30-day period "
                                    "does not contain enough data."
                                )

                            else:

                                total_current = (
                                    current[
                                        metric_column
                                    ].sum()
                                )

                                total_previous = (
                                    previous[
                                        metric_column
                                    ].sum()
                                    if not previous.empty
                                    else 0
                                )

                                overall_change = (
                                    total_current
                                    - total_previous
                                )

                                # Business dimensions
                                dimensions = [
                                    "product",
                                    "product_name",
                                    "category",
                                    "region",
                                    "customer",
                                    "customer_id",
                                    "segment",
                                    "channel",
                                    "campaign",
                                ]

                                available_dimensions = []

                                for candidate in dimensions:

                                    column = detect_root_column(
                                        data,
                                        [candidate]
                                    )

                                    if (
                                        column
                                        and column not in
                                        available_dimensions
                                    ):

                                        available_dimensions.append(
                                            column
                                        )

                                results = find_root_causes(
                                    current,
                                    previous,
                                    metric_column,
                                    available_dimensions
                                )

                                insights = (
                                    generate_root_cause_insights(
                                        results,
                                        overall_change,
                                        metric_column
                                    )
                                )

                                has_data = True

                except Exception as exc:

                    error_message = (
                        f"Unable to analyze this dataset: {exc}"
                    )

    context = {

        "datasets": datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            selected_version,

        "has_data":
            has_data,

        "error_message":
            error_message,

        "results":
            results,

        "insights":
            insights,

        "total_current":
            round(float(total_current), 2),

        "total_previous":
            round(float(total_previous), 2),

        "overall_change":
            round(float(overall_change), 2),

        "current_start":
            current_start,

        "current_end":
            current_end,

        "previous_start":
            previous_start,

        "previous_end":
            previous_end,

        "date_column":
            date_column,

        "metric_column":
            metric_column,
    }

    return render(
        request,
        "advanced_insights/root_cause.html",
        context
    )

# ============================================================
# CUSTOMER RISK ANALYSIS
# ============================================================

@login_required
def customer_risk_analysis(request):

    # ========================================================
    # ONLY CUSTOMER DATASETS
    # ========================================================
    #
    # Customer Risk Analysis must never show:
    # Sales
    # Products
    # Marketing
    # Financial
    # Returns
    # Regional
    #
    # It only works with datasets whose dataset_type is
    # "Customers".
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            dataset_type__iexact="Customers",
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    risk_data = pd.DataFrame()

    summary = {
        "total_customers": 0,
        "high_risk_customers": 0,
        "at_risk_customers": 0,
        "medium_risk_customers": 0,
        "low_risk_customers": 0,
        "risk_rate": 0,
        "average_risk_score": 0,
    }

    distribution = []
    insights = []
    top_risky_customers = []

    customer_column = None
    date_column = None
    metric_column = None
    quantity_column = None

    analysis_date = None

    # ========================================================
    # DATASET SELECTION
    # ========================================================

    dataset_id = request.GET.get("dataset")

    if dataset_id:

        try:

            selected_dataset = datasets.get(
                id=dataset_id
            )

        except Dataset.DoesNotExist:

            selected_dataset = datasets.first()

    else:

        selected_dataset = datasets.first()

    # ========================================================
    # LOAD SELECTED CUSTOMER DATASET
    # ========================================================

    if selected_dataset:

        try:

            # =================================================
            # PREFER LATEST CLEANED VERSION
            # =================================================

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    version_type="Cleaned",
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

            # =================================================
            # FALLBACK TO CURRENT VERSION
            # =================================================

            if not selected_version:

                selected_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=selected_dataset,
                        is_current=True,
                    )
                    .order_by(
                        "-version_number",
                        "-created_at",
                    )
                    .first()
                )

            # =================================================
            # DETERMINE FILE
            # =================================================

            file_path = None

            if selected_version:

                if selected_version.file:

                    file_path = (
                        selected_version.file.path
                    )

            elif selected_dataset.file:

                file_path = (
                    selected_dataset.file.path
                )

            # =================================================
            # FILE CHECK
            # =================================================

            if not file_path:

                error_message = (
                    "No dataset file is available "
                    "for Customer Risk Analysis."
                )

            else:

                # =================================================
                # READ FILE
                # =================================================

                filename = file_path.lower()

                if filename.endswith(".csv"):

                    df = pd.read_csv(
                        file_path
                    )

                elif (
                    filename.endswith(".xlsx")
                    or filename.endswith(".xls")
                ):

                    df = pd.read_excel(
                        file_path
                    )

                else:

                    df = pd.DataFrame()

                    error_message = (
                        "Unsupported dataset format. "
                        "Please use CSV or Excel."
                    )

                # =================================================
                # DATAFRAME VALIDATION
                # =================================================

                if not df.empty:

                    # =============================================
                    # CUSTOMER COLUMN
                    # =============================================

                    customer_column = (
                        detect_customer_column(
                            df,
                            [
                                "customer",
                                "customer_id",
                                "customer_name",
                                "customer_code",
                                "client",
                                "client_id",
                                "buyer",
                                "buyer_id",
                                "user_id",
                            ],
                        )
                    )

                    # =============================================
                    # DATE COLUMN
                    # =============================================

                    date_column = (
                        detect_customer_column(
                            df,
                            [
                                "date",
                                "order_date",
                                "transaction_date",
                                "sale_date",
                                "purchase_date",
                                "created_at",
                                "invoice_date",
                                "last_purchase_date",
                            ],
                        )
                    )

                    # =============================================
                    # REVENUE / SALES COLUMN
                    # =============================================

                    metric_column = (
                        detect_customer_column(
                            df,
                            [
                                "sales",
                                "sale",
                                "revenue",
                                "total_sales",
                                "total_revenue",
                                "net_sales",
                                "amount",
                                "order_value",
                                "purchase_amount",
                                "customer_value",
                            ],
                        )
                    )

                    # =============================================
                    # QUANTITY COLUMN
                    # =============================================

                    quantity_column = (
                        detect_customer_column(
                            df,
                            [
                                "quantity",
                                "qty",
                                "units",
                                "units_sold",
                                "order_quantity",
                                "total_quantity",
                            ],
                        )
                    )

                    # =============================================
                    # REQUIRED COLUMN VALIDATION
                    # =============================================

                    missing_columns = []

                    if not customer_column:

                        missing_columns.append(
                            "Customer"
                        )

                    if not date_column:

                        missing_columns.append(
                            "Date"
                        )

                    if not metric_column:

                        missing_columns.append(
                            "Sales / Revenue"
                        )

                    # =============================================
                    # MISSING COLUMN MESSAGE
                    # =============================================

                    if missing_columns:

                        error_message = (
                            "The selected Customer dataset "
                            "is missing the required column(s): "
                            + ", ".join(
                                missing_columns
                            )
                            + "."
                        )

                    else:

                        # =========================================
                        # RUN CUSTOMER RISK ENGINE
                        # =========================================

                        (
                            risk_data,
                            summary,
                            distribution,
                            insights,
                        ) = run_customer_risk_analysis(

                            df=df,

                            customer_column=(
                                customer_column
                            ),

                            date_column=(
                                date_column
                            ),

                            metric_column=(
                                metric_column
                            ),

                            quantity_column=(
                                quantity_column
                            ),
                        )

                        # =========================================
                        # VALID RESULT
                        # =========================================

                        if not risk_data.empty:

                            has_data = True

                            # =====================================
                            # ANALYSIS DATE
                            # =====================================

                            try:

                                analysis_date = (
                                    pd.to_datetime(
                                        risk_data[
                                            "last_purchase"
                                        ]
                                    ).max()
                                )

                                if pd.notna(
                                    analysis_date
                                ):

                                    analysis_date = (
                                        analysis_date.strftime(
                                            "%d %b %Y"
                                        )
                                    )

                            except Exception:

                                analysis_date = None

                            # =====================================
                            # TOP 10 RISKY CUSTOMERS
                            # =====================================

                            top_data = (
                                risk_data
                                .sort_values(
                                    "risk_score",
                                    ascending=False,
                                )
                                .head(10)
                            )

                            for _, row in (
                                top_data.iterrows()
                            ):

                                # -----------------------------
                                # Last purchase date
                                # -----------------------------

                                last_purchase = (
                                    row[
                                        "last_purchase"
                                    ]
                                )

                                try:

                                    last_purchase = (
                                        pd.to_datetime(
                                            last_purchase
                                        ).strftime(
                                            "%d %b %Y"
                                        )
                                    )

                                except Exception:

                                    last_purchase = "-"

                                # -----------------------------
                                # Customer record
                                # -----------------------------

                                top_risky_customers.append(
                                    {
                                        "customer": str(
                                            row[
                                                "customer"
                                            ]
                                        ),

                                        "last_purchase": (
                                            last_purchase
                                        ),

                                        "recency": int(
                                            row[
                                                "recency"
                                            ]
                                        ),

                                        "frequency": int(
                                            row[
                                                "frequency"
                                            ]
                                        ),

                                        "monetary": round(
                                            float(
                                                row[
                                                    "monetary"
                                                ]
                                            ),
                                            2,
                                        ),

                                        "risk_score": round(
                                            float(
                                                row[
                                                    "risk_score"
                                                ]
                                            ),
                                            1,
                                        ),

                                        "risk_level": (
                                            row[
                                                "risk_level"
                                            ]
                                        ),

                                        "recommended_action": (
                                            row[
                                                "recommended_action"
                                            ]
                                        ),
                                    }
                                )

                        else:

                            error_message = (
                                "No valid customer transaction "
                                "records were available for "
                                "Customer Risk Analysis."
                            )

        except Exception as exc:

            error_message = (
                "Customer Risk Analysis failed: "
                f"{exc}"
            )

    # ========================================================
    # NO CUSTOMER DATASETS
    # ========================================================

    else:

        error_message = (
            "No Customer datasets are available. "
            "Please upload a dataset under the "
            "'Customers' data category in Data Management."
        )

    # ========================================================
    # CHART DATA
    # ========================================================

    risk_labels = [
        item["name"]
        for item in distribution
    ]

    risk_values = [
        item["count"]
        for item in distribution
    ]

    risk_percentages = [
        item["percentage"]
        for item in distribution
    ]

    # ========================================================
    # TOP RISK CUSTOMER CHART
    # ========================================================

    risky_customer_labels = [
        item["customer"]
        for item in top_risky_customers[:8]
    ]

    risky_customer_scores = [
        item["risk_score"]
        for item in top_risky_customers[:8]
    ]

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # CUSTOMER DATASETS ONLY
        # ----------------------------------------------------

        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "selected_version": (
            selected_version
        ),

        # ----------------------------------------------------
        # STATE
        # ----------------------------------------------------

        "has_data": has_data,

        "error_message": error_message,

        # ----------------------------------------------------
        # DETECTED COLUMNS
        # ----------------------------------------------------

        "customer_column": (
            customer_column
        ),

        "date_column": (
            date_column
        ),

        "metric_column": (
            metric_column
        ),

        "quantity_column": (
            quantity_column
        ),

        # ----------------------------------------------------
        # SUMMARY
        # ----------------------------------------------------

        "total_customers": (
            summary[
                "total_customers"
            ]
        ),

        "high_risk_customers": (
            summary[
                "high_risk_customers"
            ]
        ),

        "at_risk_customers": (
            summary[
                "at_risk_customers"
            ]
        ),

        "medium_risk_customers": (
            summary[
                "medium_risk_customers"
            ]
        ),

        "low_risk_customers": (
            summary[
                "low_risk_customers"
            ]
        ),

        "risk_rate": (
            summary[
                "risk_rate"
            ]
        ),

        "average_risk_score": (
            summary[
                "average_risk_score"
            ]
        ),

        # ----------------------------------------------------
        # RISK DISTRIBUTION
        # ----------------------------------------------------

        "risk_distribution": (
            distribution
        ),

        # ----------------------------------------------------
        # TOP RISKY CUSTOMERS
        # ----------------------------------------------------

        "top_risky_customers": (
            top_risky_customers
        ),

        # ----------------------------------------------------
        # BUSINESS INSIGHTS
        # ----------------------------------------------------

        "customer_risk_insights": (
            insights
        ),

        # ----------------------------------------------------
        # ANALYSIS DATE
        # ----------------------------------------------------

        "analysis_date": (
            analysis_date
        ),

        # ----------------------------------------------------
        # CHART JSON
        # ----------------------------------------------------

        "risk_labels": json.dumps(
            risk_labels
        ),

        "risk_values": json.dumps(
            risk_values
        ),

        "risk_percentages": json.dumps(
            risk_percentages
        ),

        "risky_customer_labels": json.dumps(
            risky_customer_labels
        ),

        "risky_customer_scores": json.dumps(
            risky_customer_scores
        ),
    }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "advanced_insights/customer_risk.html",
        context,
    )
from .services.opportunity_detection import (
    detect_column as detect_opportunity_column,
    run_opportunity_detection,
)



@login_required
def opportunity_detection(request):

    # ========================================================
    # OPPORTUNITY DETECTION DATASET CATEGORIES
    # ========================================================
    #
    # Opportunity Detection should NOT show every dataset.
    #
    # Allowed categories:
    #   Products
    #   Customers
    #   Regional
    #   Marketing
    #
    # Excluded:
    #   Payments
    #   Returns
    #   Expenses
    #   Financial
    #   Other unrelated datasets
    # ========================================================

    OPPORTUNITY_DATASET_TYPES = [
        "Products",
        "Customers",
        "Regional",
        "Marketing",
    ]

    # ========================================================
    # DATASETS
    # ========================================================

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            dataset_type__in=OPPORTUNITY_DATASET_TYPES,
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None

    has_data = False
    error_message = ""

    opportunities = []

    summary = {
        "total_opportunities": 0,
        "high_opportunities": 0,
        "strong_opportunities": 0,
        "emerging_opportunities": 0,
        "average_score": 0,
    }

    insights = []

    date_column = None
    sales_column = None
    quantity_column = None

    analysis_date = None

    current_start = None
    current_end = None

    # ========================================================
    # DATASET SELECTION
    # ========================================================

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:

        try:

            # ------------------------------------------------
            # Important:
            # get() works only inside the allowed queryset.
            #
            # Therefore a user cannot manually pass the ID
            # of an excluded dataset such as Payments or
            # Returns and make it appear here.
            # ------------------------------------------------

            selected_dataset = (
                datasets.get(
                    id=dataset_id
                )
            )

        except Dataset.DoesNotExist:

            selected_dataset = (
                datasets.first()
            )

    else:

        selected_dataset = (
            datasets.first()
        )

    # ========================================================
    # LOAD SELECTED DATASET
    # ========================================================

    if selected_dataset:

        try:

            # =================================================
            # LATEST CLEANED VERSION
            # =================================================

            selected_version = (
                DatasetVersion.objects
                .filter(
                    dataset=selected_dataset,
                    version_type="Cleaned",
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
                .first()
            )

            # =================================================
            # FALLBACK CURRENT VERSION
            # =================================================

            if not selected_version:

                selected_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=selected_dataset,
                        is_current=True,
                    )
                    .order_by(
                        "-version_number",
                        "-created_at",
                    )
                    .first()
                )

            # =================================================
            # DETERMINE FILE
            # =================================================

            file_path = None

            if selected_version:

                if selected_version.file:

                    file_path = (
                        selected_version
                        .file
                        .path
                    )

            elif selected_dataset.file:

                file_path = (
                    selected_dataset
                    .file
                    .path
                )

            # =================================================
            # FILE VALIDATION
            # =================================================

            if not file_path:

                error_message = (
                    "No dataset file is available "
                    "for Opportunity Detection."
                )

            else:

                # =================================================
                # READ DATASET
                # =================================================

                filename = (
                    file_path.lower()
                )

                if filename.endswith(".csv"):

                    df = pd.read_csv(
                        file_path
                    )

                elif (
                    filename.endswith(".xlsx")
                    or filename.endswith(".xls")
                ):

                    df = pd.read_excel(
                        file_path
                    )

                else:

                    df = pd.DataFrame()

                    error_message = (
                        "Unsupported dataset format. "
                        "Please use CSV or Excel."
                    )

                # =================================================
                # VALIDATE DATAFRAME
                # =================================================

                if not df.empty:

                    # =================================================
                    # DETECT DATE COLUMN
                    # =================================================

                    date_column = (
                        detect_opportunity_column(
                            df,
                            [
                                "date",
                                "order_date",
                                "transaction_date",
                                "sale_date",
                                "purchase_date",
                                "created_at",
                                "invoice_date",
                            ],
                        )
                    )

                    # =================================================
                    # DETECT SALES / REVENUE
                    # =================================================

                    sales_column = (
                        detect_opportunity_column(
                            df,
                            [
                                "sales",
                                "sale",
                                "revenue",
                                "total_sales",
                                "total_revenue",
                                "net_sales",
                                "amount",
                                "order_value",
                                "purchase_amount",
                            ],
                        )
                    )

                    # =================================================
                    # DETECT QUANTITY
                    # =================================================

                    quantity_column = (
                        detect_opportunity_column(
                            df,
                            [
                                "quantity",
                                "qty",
                                "units",
                                "units_sold",
                                "order_quantity",
                                "total_quantity",
                            ],
                        )
                    )

                    # =================================================
                    # REQUIRED COLUMNS
                    # =================================================

                    missing_columns = []

                    if not date_column:

                        missing_columns.append(
                            "Date"
                        )

                    if not sales_column:

                        missing_columns.append(
                            "Sales / Revenue"
                        )

                    if missing_columns:

                        error_message = (
                            "Opportunity Detection "
                            "requires: "
                            + ", ".join(
                                missing_columns
                            )
                            + "."
                        )

                    else:

                        # =================================================
                        # CATEGORY-SPECIFIC DIMENSIONS
                        # =================================================
                        #
                        # Do NOT analyze every possible dimension.
                        #
                        # The selected dataset category determines what
                        # Smart BI should investigate.
                        # =================================================

                        dataset_category = str(
                            selected_dataset.dataset_type
                        ).strip().lower()

                        dimensions = []

                        # =================================================
                        # PRODUCTS
                        # =================================================

                        if dataset_category == "products":

                            product_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "product",
                                        "product_name",
                                        "product_id",
                                        "item",
                                        "item_name",
                                        "sku",
                                    ],
                                )
                            )

                            category_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "category",
                                        "product_category",
                                        "product_type",
                                    ],
                                )
                            )

                            if product_column:

                                dimensions.append(
                                    product_column
                                )

                            if (
                                category_column
                                and category_column
                                not in dimensions
                            ):

                                dimensions.append(
                                    category_column
                                )

                        # =================================================
                        # CUSTOMERS
                        # =================================================

                        elif dataset_category == "customers":

                            customer_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "customer",
                                        "customer_id",
                                        "customer_name",
                                        "client",
                                        "client_id",
                                        "buyer",
                                        "buyer_id",
                                        "user_id",
                                    ],
                                )
                            )

                            segment_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "segment",
                                        "customer_segment",
                                        "customer_type",
                                    ],
                                )
                            )

                            if customer_column:

                                dimensions.append(
                                    customer_column
                                )

                            if (
                                segment_column
                                and segment_column
                                not in dimensions
                            ):

                                dimensions.append(
                                    segment_column
                                )

                        # =================================================
                        # REGIONAL
                        # =================================================

                        elif dataset_category == "regional":

                            region_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "region",
                                        "area",
                                        "territory",
                                        "location",
                                        "state",
                                        "city",
                                        "market",
                                    ],
                                )
                            )

                            if region_column:

                                dimensions.append(
                                    region_column
                                )

                        # =================================================
                        # MARKETING
                        # =================================================

                        elif dataset_category == "marketing":

                            campaign_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "campaign",
                                        "campaign_name",
                                        "campaign_id",
                                        "marketing_campaign",
                                    ],
                                )
                            )

                            channel_column = (
                                detect_opportunity_column(
                                    df,
                                    [
                                        "channel",
                                        "marketing_channel",
                                        "campaign_channel",
                                        "ad_channel",
                                        "source",
                                        "medium",
                                    ],
                                )
                            )

                            if campaign_column:

                                dimensions.append(
                                    campaign_column
                                )

                            if (
                                channel_column
                                and channel_column
                                not in dimensions
                            ):

                                dimensions.append(
                                    channel_column
                                )

                        # =================================================
                        # CATEGORY VALIDATION
                        # =================================================

                        if not dimensions:

                            error_message = (
                                "No suitable business dimension "
                                "was found in the selected "
                                f"{selected_dataset.dataset_type} "
                                "dataset for Opportunity Detection."
                            )

                        else:

                            # =================================================
                            # RUN OPPORTUNITY ENGINE
                            # =================================================

                            result = run_opportunity_detection(
    df=df,
    date_column=date_column,
    sales_column=sales_column,
    quantity_column=quantity_column,
    dimension_columns=dimensions,
    category_type=selected_dataset.dataset_type,
)

                            # =================================================
                            # RESULT
                            # =================================================

                            opportunities = (
                                result[
                                    "opportunities"
                                ]
                            )

                            summary = (
                                result[
                                    "summary"
                                ]
                            )

                            insights = (
                                result[
                                    "insights"
                                ]
                            )

                            current_start = (
                                result[
                                    "current_start"
                                ]
                            )

                            current_end = (
                                result[
                                    "current_end"
                                ]
                            )

                            # =================================================
                            # DATA AVAILABLE
                            # =================================================

                            if opportunities:

                                has_data = True

                            else:

                                if not insights:

                                    error_message = (
                                        "No significant business "
                                        "opportunities were "
                                        "identified in the selected "
                                        "dataset."
                                    )

                            # =================================================
                            # ANALYSIS DATE
                            # =================================================

                            if current_end is not None:

                                try:

                                    analysis_date = (
                                        pd.to_datetime(
                                            current_end
                                        ).strftime(
                                            "%d %b %Y"
                                        )
                                    )

                                except Exception:

                                    analysis_date = None

        except Exception as exc:

            error_message = (
                "Opportunity Detection failed: "
                f"{exc}"
            )

    # ========================================================
    # NO ALLOWED DATASETS
    # ========================================================

    else:

        error_message = (
            "No suitable datasets are available for "
            "Opportunity Detection. Please upload a "
            "Products, Customers, Regional, or Marketing "
            "dataset from Data Management."
        )

    # ========================================================
    # CHART DATA
    # ========================================================

    chart_opportunities = (
        opportunities[:10]
    )

    opportunity_labels = [
        item["category"]
        for item in chart_opportunities
    ]

    opportunity_scores = [
        item["opportunity_score"]
        for item in chart_opportunities
    ]

    opportunity_growth = [
        item["growth_percent"]
        for item in chart_opportunities
    ]

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # ====================================================
        # DATASETS
        # ====================================================

        "datasets": datasets,

        "selected_dataset": (
            selected_dataset
        ),

        "selected_version": (
            selected_version
        ),

        # ====================================================
        # STATE
        # ====================================================

        "has_data": has_data,

        "error_message": (
            error_message
        ),

        # ====================================================
        # CATEGORY
        # ====================================================

        "dataset_category": (
            selected_dataset.dataset_type
            if selected_dataset
            else None
        ),

        # ====================================================
        # COLUMNS
        # ====================================================

        "date_column": (
            date_column
        ),

        "sales_column": (
            sales_column
        ),

        "quantity_column": (
            quantity_column
        ),

        # ====================================================
        # SUMMARY
        # ====================================================

        "total_opportunities": (
            summary[
                "total_opportunities"
            ]
        ),

        "high_opportunities": (
            summary[
                "high_opportunities"
            ]
        ),

        "strong_opportunities": (
            summary[
                "strong_opportunities"
            ]
        ),

        "emerging_opportunities": (
            summary[
                "emerging_opportunities"
            ]
        ),

        "average_opportunity_score": (
            summary[
                "average_score"
            ]
        ),

        # ====================================================
        # OPPORTUNITIES
        # ====================================================

        "opportunities": (
            opportunities
        ),

        # ====================================================
        # INSIGHTS
        # ====================================================

        "opportunity_insights": (
            insights
        ),

        # ====================================================
        # PERIOD
        # ====================================================

        "current_start": (
            current_start
        ),

        "current_end": (
            current_end
        ),

        "analysis_date": (
            analysis_date
        ),

        # ====================================================
        # CHART JSON
        # ====================================================

        "opportunity_labels": (
            json.dumps(
                opportunity_labels
            )
        ),

        "opportunity_scores": (
            json.dumps(
                opportunity_scores
            )
        ),

        "opportunity_growth": (
            json.dumps(
                opportunity_growth
            )
        ),
    }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "advanced_insights/opportunity_detection.html",
        context,
    )

