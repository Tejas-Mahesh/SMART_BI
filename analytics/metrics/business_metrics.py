"""
Business Intelligence Metrics
=============================

Business Intelligence only.

IMPORTANT ARCHITECTURE
----------------------

Business Intelligence uses EXACTLY ONE selected dataset per dataset type.

Example:

    Sales:
        Sales January
        Sales February
        Sales Final

The Business Intelligence page selects ONE dataset.

Only the analytics result belonging to the selected dataset is used.

Business Intelligence does NOT:

    - concatenate multiple datasets
    - aggregate multiple datasets of the same type
    - sum KPIs from multiple files
    - average KPIs from multiple files
    - merge chart rows from multiple files
    - treat different dataset types as one DataFrame

Individual analytics modules remain responsible for calculating the
metrics and charts for their own dataset.

This module only:

    1. Reads the selected analytics result for each dataset type.
    2. Exposes its metrics to Business Intelligence.
    3. Exposes its charts to Business Intelligence.
    4. Calculates a small number of cross-category derived ratios.
    5. Generates descriptive Business Intelligence insights.

Supported source structure
--------------------------

Preferred:

    {
        "Sales": {
            "dataset_id": 1,
            "dataset_name": "Sales Final",
            "metrics": {...},
            "chart_data": {...},
            "dataframe_available": True,
        },

        "Customers": {
            "dataset_id": 2,
            "dataset_name": "Customers Final",
            "metrics": {...},
            "chart_data": {...},
            "dataframe_available": True,
        },
    }

Compatibility:

    {
        "Sales": [
            {
                "dataset_id": 1,
                "dataset_name": "Sales Final",
                "metrics": {...},
                "chart_data": {...},
            }
        ]
    }

If a list is received, ONLY THE FIRST usable result is used.

It is never aggregated with another result.

Missing data
------------

Missing dataset:
    metric = None
    chart = []

Missing metric:
    metric = None

Missing chart:
    chart = []

Zero is a valid value and is never treated as missing.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


# =====================================================================
# PRIMARY SOURCE DEFINITIONS
# =====================================================================

PRIMARY_SOURCES = {
    "sales": "Sales",
    "revenue": "Sales",
    "orders": "Sales",
    "units": "Sales",
    "average_order_value": "Sales",

    "customers": "Customers",
    "active_customers": "Customers",
    "repeat_customers": "Customers",
    "customer_value": "Customers",

    "products": "Products",
    "product_count": "Products",

    "regions": "Regional",
    "regional_sales": "Regional",

    "marketing_cost": "Marketing",
    "marketing_roi": "Marketing",
    "marketing_roas": "Marketing",
    "campaigns": "Marketing",

    "profit": "Financial",
    "gross_profit": "Financial",
    "net_profit": "Financial",
    "cost": "Financial",
    "expenses": "Financial",
    "cash_flow": "Financial",

    "returns": "Returns",
    "return_value": "Returns",
    "return_rate": "Returns",
}


SUPPORTED_DATASET_TYPES = (
    "Sales",
    "Customers",
    "Products",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
)


# =====================================================================
# DATASET TYPE NORMALIZATION
# =====================================================================

_DATASET_TYPE_ALIASES = {
    "sales": "Sales",
    "revenue": "Sales",
    "orders": "Sales",

    "customers": "Customers",
    "customer": "Customers",

    "products": "Products",
    "product": "Products",

    "regional": "Regional",
    "region": "Regional",

    "marketing": "Marketing",
    "campaign": "Marketing",

    "financial": "Financial",
    "finance": "Financial",

    "returns": "Returns",
    "return": "Returns",
}


def _normalise_dataset_type(dataset_type: Any) -> Optional[str]:
    """
    Convert dataset-type aliases into the canonical dataset type.
    """
    if dataset_type is None:
        return None

    value = str(dataset_type).strip()

    if not value:
        return None

    return _DATASET_TYPE_ALIASES.get(
        value.lower(),
        value if value in SUPPORTED_DATASET_TYPES else None,
    )


# =====================================================================
# GENERIC HELPERS
# =====================================================================

def _is_available(value: Any) -> bool:
    """
    Return True when a value is actually available.

    Important:
        0 is available.
        False is available.
        Empty strings are considered unavailable.
        None is unavailable.
    """
    if value is None:
        return False

    if isinstance(value, str) and not value.strip():
        return False

    return True


def _safe_number(value: Any) -> Optional[float]:
    """
    Safely convert a value to float.

    Invalid values become None rather than zero.
    """
    if value is None:
        return None

    if isinstance(value, bool):
        return float(value)

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_number(value: Optional[float]) -> Optional[float]:
    """
    Convert integer-valued floats into integers.
    """
    if value is None:
        return None

    try:
        if float(value).is_integer():
            return int(value)
    except (TypeError, ValueError):
        pass

    return value


# =====================================================================
# SOURCE RESULT NORMALIZATION
# =====================================================================

def _is_result_dict(value: Any) -> bool:
    """
    Determine whether a dictionary actually looks like an analytics
    result rather than a wrapper.
    """
    if not isinstance(value, dict):
        return False

    return any(
        key in value
        for key in (
            "metrics",
            "chart_data",
            "dataframe_available",
            "dataset_id",
            "dataset_name",
            "version_id",
        )
    )


def _result_is_usable(result: Optional[Dict[str, Any]]) -> bool:
    """
    Determine whether an analytics result contains usable information.

    We deliberately do NOT assume that a missing dataframe_available
    means the dataset is available.

    A result is usable when it contains actual analytics information.
    """
    if not isinstance(result, dict):
        return False

    metrics = result.get("metrics")
    chart_data = result.get("chart_data")

    dataframe_available = result.get(
        "dataframe_available"
    )

    if dataframe_available is True:
        return True

    if isinstance(metrics, dict) and bool(metrics):
        return True

    if isinstance(chart_data, dict):
        if any(
            isinstance(value, list) and value
            for value in chart_data.values()
        ):
            return True

    return False


def _normalise_source_results(
    source_results: Optional[Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Normalize source results to exactly ONE result per dataset type.

    Preferred:

        {
            "Sales": {...},
            "Customers": {...},
        }

    Compatibility:

        {
            "Sales": [{...}, {...}],
        }

    Only the first usable result is selected.

    No aggregation is performed.
    """
    source_results = source_results or {}

    normalized: Dict[str, Dict[str, Any]] = {}

    for raw_dataset_type, value in source_results.items():

        dataset_type = _normalise_dataset_type(
            raw_dataset_type
        )

        if not dataset_type:
            continue

        selected: Optional[Dict[str, Any]] = None

        # -------------------------------------------------------------
        # Direct result
        # -------------------------------------------------------------
        if isinstance(value, dict):

            wrapped_results = value.get("results")

            if isinstance(
                wrapped_results,
                (list, tuple),
            ):
                for item in wrapped_results:
                    if _result_is_usable(item):
                        selected = item
                        break
            elif _is_result_dict(value):
                selected = value

        # -------------------------------------------------------------
        # Compatibility list
        # -------------------------------------------------------------
        elif isinstance(
            value,
            (list, tuple),
        ):

            for item in value:
                if _result_is_usable(item):
                    selected = item
                    break

        if selected is not None:
            normalized[dataset_type] = selected

    return normalized


def _get_source_result(
    source_results: Dict[str, Any],
    dataset_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Return exactly ONE selected result for a dataset type.

    Never aggregates multiple results.
    """
    source_results = source_results or {}

    target = _normalise_dataset_type(
        dataset_type
    )

    if not target:
        return None

    # First check canonical normalized keys.
    normalized = _normalise_source_results(
        source_results
    )

    result = normalized.get(target)

    if result is not None:
        return result

    return None


def _available_result(
    source_results: Dict[str, Any],
    dataset_type: str,
) -> Optional[Dict[str, Any]]:
    """
    Return the selected result only when it contains usable data.
    """
    result = _get_source_result(
        source_results,
        dataset_type,
    )

    if not result:
        return None

    if not _result_is_usable(result):
        return None

    return result


def _available_results(
    source_results: Dict[str, Any],
    dataset_type: str,
) -> List[Dict[str, Any]]:
    """
    Compatibility helper.

    Returns at most ONE result.
    """
    result = _available_result(
        source_results,
        dataset_type,
    )

    return [result] if result else []


# =====================================================================
# METRIC HELPERS
# =====================================================================

def _metric_from_source(
    source_results: Dict[str, Any],
    dataset_type: str,
    metric_name: str,
) -> Tuple[Any, Optional[str]]:
    """
    Return one metric from the selected dataset.
    """
    result = _available_result(
        source_results,
        dataset_type,
    )

    if not result:
        return None, None

    metrics = result.get("metrics") or {}

    if metric_name not in metrics:
        return None, None

    value = metrics.get(metric_name)

    if not _is_available(value):
        return None, None

    return value, _source_label(
        dataset_type,
        result,
    )


def _first_available(
    sources: Iterable[Dict[str, Any]],
    key: str,
) -> Tuple[Any, Optional[str]]:
    """
    Return the first available metric.

    No aggregation is performed.
    """
    for source in sources:

        metrics = source.get("metrics") or {}

        if key not in metrics:
            continue

        value = metrics.get(key)

        if _is_available(value):
            return (
                value,
                source.get("dataset_type"),
            )

    return None, None


def _set_metric(
    metrics: Dict[str, Any],
    sources: Dict[str, Optional[str]],
    key: str,
    value: Any,
    source: Optional[str],
) -> None:
    """
    Store a metric and its source.
    """
    metrics[key] = value
    sources[key] = source


def _selected_dataset_name(
    result: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    Return the selected dataset name.
    """
    if not result:
        return None

    name = (
        result.get("dataset_name")
        or result.get("name")
    )

    if name is None:
        return None

    text = str(name).strip()

    return text or None


def _source_label(
    dataset_type: str,
    result: Optional[Dict[str, Any]],
) -> Optional[str]:
    """
    Build readable source metadata.
    """
    if not result:
        return None

    dataset_name = _selected_dataset_name(
        result
    )

    if dataset_name:
        return dataset_name

    canonical_type = _normalise_dataset_type(
        dataset_type
    )

    return canonical_type or str(dataset_type)


def _source_label_for_types(
    source_results: Dict[str, Any],
    dataset_types: Sequence[str],
) -> Optional[str]:
    """
    Build a readable source label for a derived metric.

    Example:

        Sales Final + Customers Final
    """
    labels: List[str] = []

    for dataset_type in dataset_types:

        result = _available_result(
            source_results,
            dataset_type,
        )

        if not result:
            continue

        label = _source_label(
            dataset_type,
            result,
        )

        if label and label not in labels:
            labels.append(label)

    if not labels:
        return None

    return " + ".join(labels)


def _metric_value(
    source_results: Dict[str, Any],
    dataset_type: str,
    metric_names: Sequence[str],
) -> Tuple[Optional[float], Optional[str]]:
    """
    Return the first available numeric metric from ONE selected dataset.

    The metric names are aliases for the same selected dataset.
    """
    result = _available_result(
        source_results,
        dataset_type,
    )

    if not result:
        return None, None

    source = _source_label(
        dataset_type,
        result,
    )

    metrics = result.get("metrics") or {}

    for metric_name in metric_names:

        if metric_name not in metrics:
            continue

        value = _safe_number(
            metrics.get(metric_name)
        )

        if value is not None:
            return value, source

    return None, None


def _copy_source_metric(
    source_results: Dict[str, Any],
    dataset_type: str,
    target_metrics: Dict[str, Any],
    metric_sources: Dict[str, Optional[str]],
    target_key: str,
    source_keys: Sequence[str],
) -> None:
    """
    Copy one metric from one selected analytics result.

    No aggregation occurs.
    """
    result = _available_result(
        source_results,
        dataset_type,
    )

    if not result:
        target_metrics[target_key] = None
        metric_sources[target_key] = None
        return

    source_metrics = result.get("metrics") or {}

    source = _source_label(
        dataset_type,
        result,
    )

    for key in source_keys:

        if key not in source_metrics:
            continue

        value = source_metrics.get(key)

        if _is_available(value):

            target_metrics[target_key] = value
            metric_sources[target_key] = source

            return

    target_metrics[target_key] = None
    metric_sources[target_key] = None


def _derive_ratio(
    numerator: Optional[float],
    denominator: Optional[float],
    source: Optional[str],
    multiplier: float = 1.0,
) -> Tuple[Optional[float], Optional[str]]:
    """
    Safely calculate a ratio.
    """
    if (
        numerator is None
        or denominator is None
        or denominator == 0
    ):
        return None, None

    value = (
        numerator
        / denominator
        * multiplier
    )

    return (
        _clean_number(value),
        source,
    )


# =====================================================================
# CHART HELPERS
# =====================================================================

def _chart_group_candidates(
    chart_key: str,
) -> List[str]:

    if chart_key in {
        "sales_trend",
        "registration_trend",
        "revenue_trend",
        "financial_trend",
        "cash_flow_trend",
        "returns_trend",
        "product_sales_trend",
        "sales_by_date",
        "marketing_by_date",
    }:
        return [
            "date",
            "Date",
            "month",
            "Month",
            "period",
            "Period",
            "label",
            "Label",
        ]

    if chart_key in {
        "sales_by_region",
        "units_by_region",
        "customers_by_region",
        "profit_by_region",
        "returns_by_region",
    }:
        return [
            "region",
            "Region",
            "name",
            "Name",
        ]

    if chart_key in {
        "sales_by_category",
        "profit_by_category",
        "returns_by_category",
    }:
        return [
            "category",
            "Category",
            "name",
            "Name",
        ]

    if chart_key in {
        "top_products",
        "sales_by_product",
        "returns_by_product",
    }:
        return [
            "product",
            "product_name",
            "Product",
            "Product_Name",
            "Product Name",
            "name",
            "Name",
        ]

    if chart_key in {
        "sales_by_campaign",
        "marketing_campaigns",
        "cost_by_campaign",
        "conversions_by_campaign",
        "roi_by_campaign",
    }:
        return [
            "campaign",
            "campaign_name",
            "Campaign",
            "Campaign_Name",
            "Campaign Name",
            "name",
            "Name",
        ]

    if chart_key in {
        "channel_performance",
        "marketing_performance",
    }:
        return [
            "channel",
            "Channel",
            "name",
            "Name",
        ]

    if chart_key in {
        "customers_by_segment",
        "customer_segments",
    }:
        return [
            "segment",
            "Segment",
            "name",
            "Name",
        ]

    if chart_key == "returns_by_reason":
        return [
            "reason",
            "Reason",
            "return_reason",
            "Return_Reason",
            "name",
            "Name",
        ]

    if chart_key in {
        "return_status",
        "status_distribution",
    }:
        return [
            "status",
            "Status",
            "return_status",
            "Return_Status",
            "name",
            "Name",
        ]

    return [
        "date",
        "Date",
        "month",
        "Month",
        "period",
        "Period",
        "region",
        "Region",
        "category",
        "Category",
        "product",
        "product_name",
        "Product",
        "Product_Name",
        "campaign",
        "campaign_name",
        "Campaign",
        "Campaign_Name",
        "channel",
        "Channel",
        "segment",
        "Segment",
        "reason",
        "Reason",
        "status",
        "Status",
        "band",
        "Band",
        "name",
        "Name",
    ]


def _find_row_key(
    row: Dict[str, Any],
    candidates: Sequence[str],
) -> Optional[str]:

    if not isinstance(row, dict):
        return None

    for candidate in candidates:

        if (
            candidate in row
            and row.get(candidate) is not None
        ):
            return candidate

    lowered = {
        str(key).strip().lower(): key
        for key in row.keys()
    }

    for candidate in candidates:

        original = lowered.get(
            str(candidate).strip().lower()
        )

        if (
            original is not None
            and row.get(original) is not None
        ):
            return original

    return None


def _normalise_group_value(
    value: Any,
) -> str:

    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.date().isoformat()

    text = str(value).strip()

    if not text:
        return ""

    try:
        parsed = datetime.fromisoformat(
            text.replace("Z", "+00:00")
        )

        return parsed.date().isoformat()

    except ValueError:
        pass

    return text


def _numeric_measure_candidates(
    chart_key: str,
) -> List[str]:

    specific = {
        "sales_trend": [
            "sales",
            "total_sales",
            "sales_amount",
            "Sales_Amount",
        ],

        "revenue_trend": [
            "revenue",
            "total_revenue",
            "sales",
            "total_sales",
            "sales_amount",
        ],

        "financial_trend": [
            "revenue",
            "total_revenue",
            "cost",
            "total_cost",
            "profit",
            "net_profit",
            "gross_profit",
        ],

        "cash_flow_trend": [
            "cash_inflow",
            "cash_outflow",
            "net_cash_flow",
            "inflow",
            "outflow",
            "net_flow",
        ],

        "returns_trend": [
            "returns",
            "total_returns",
            "returned_units",
            "return_value",
            "refund_amount",
        ],

        "sales_by_region": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
        ],

        "units_by_region": [
            "units",
            "quantity",
            "units_sold",
            "returned_units",
        ],

        "profit_by_region": [
            "profit",
            "total_profit",
            "net_profit",
            "gross_profit",
        ],

        "sales_by_category": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
        ],

        "profit_by_category": [
            "profit",
            "total_profit",
            "net_profit",
            "gross_profit",
        ],

        "top_products": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],

        "sales_by_product": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],

        "sales_by_campaign": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],

        "marketing_campaigns": [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],

        "returns_by_reason": [
            "return_value",
            "returns",
            "total_returns",
            "returned_units",
            "value",
        ],

        "returns_by_product": [
            "return_value",
            "returns",
            "total_returns",
            "returned_units",
            "value",
        ],
    }

    return specific.get(
        chart_key,
        [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "total_revenue",
            "profit",
            "total_profit",
            "net_profit",
            "gross_profit",
            "units",
            "units_sold",
            "quantity",
            "returns",
            "total_returns",
            "returned_units",
            "return_value",
            "conversions",
            "clicks",
            "impressions",
            "cost",
            "total_cost",
            "value",
        ],
    )


def _normalise_single_chart(
    value: Any,
    chart_key: str = "",
) -> List[Dict[str, Any]]:
    """
    Normalize chart data belonging to ONE selected dataset.

    This function never combines rows from different datasets.
    """
    if not isinstance(value, list):
        return []

    rows = [
        dict(row)
        for row in value
        if isinstance(row, dict)
    ]

    if not rows:
        return []

    candidates = _chart_group_candidates(
        chart_key
    )

    chronological = chart_key in {
        "sales_trend",
        "registration_trend",
        "revenue_trend",
        "financial_trend",
        "cash_flow_trend",
        "returns_trend",
        "product_sales_trend",
        "sales_by_date",
        "marketing_by_date",
    }

    if chronological:

        def chronological_key(
            item: Dict[str, Any],
        ) -> str:

            key = _find_row_key(
                item,
                candidates,
            )

            if not key:
                return ""

            return _normalise_group_value(
                item.get(key)
            )

        rows.sort(
            key=chronological_key
        )

        return rows

    numeric_sort_key = None

    for candidate in _numeric_measure_candidates(
        chart_key
    ):

        if any(
            _safe_number(
                row.get(candidate)
            ) is not None
            for row in rows
        ):
            numeric_sort_key = candidate
            break

    if numeric_sort_key:

        rows.sort(
            key=lambda item: (
                _safe_number(
                    item.get(
                        numeric_sort_key
                    )
                )
                if _safe_number(
                    item.get(
                        numeric_sort_key
                    )
                ) is not None
                else float("-inf")
            ),
            reverse=True,
        )

    return rows


def _extract_chart(
    source_results: Dict[str, Any],
    dataset_type: str,
    chart_key: str,
) -> List[Dict[str, Any]]:
    """
    Retrieve one chart from one selected dataset.
    """
    result = _available_result(
        source_results,
        dataset_type,
    )

    if not result:
        return []

    chart_data = result.get(
        "chart_data"
    ) or {}

    value = chart_data.get(
        chart_key
    )

    return _normalise_single_chart(
        value,
        chart_key=chart_key,
    )


def _extract_first_nonempty_chart(
    source_results: Dict[str, Any],
    dataset_types: Sequence[str],
    chart_keys: Sequence[str],
) -> List[Dict[str, Any]]:

    for dataset_type in dataset_types:

        for chart_key in chart_keys:

            chart = _extract_chart(
                source_results,
                dataset_type,
                chart_key,
            )

            if chart:
                return chart

    return []


# =====================================================================
# TOP ITEM HELPERS
# =====================================================================

def _top_chart_item(
    chart: Sequence[Dict[str, Any]],
    name_candidates: Sequence[str],
    value_candidates: Sequence[str],
) -> Tuple[Optional[str], Optional[float]]:

    if not chart:
        return None, None

    best_name: Optional[str] = None
    best_value: Optional[float] = None

    for row in chart:

        if not isinstance(row, dict):
            continue

        name_key = _find_row_key(
            row,
            name_candidates,
        )

        if not name_key:
            continue

        value_key = None

        for candidate in value_candidates:

            if _safe_number(
                row.get(candidate)
            ) is not None:
                value_key = candidate
                break

        if not value_key:
            continue

        name = row.get(name_key)

        value = _safe_number(
            row.get(value_key)
        )

        if (
            name is None
            or value is None
        ):
            continue

        if (
            best_value is None
            or value > best_value
        ):
            best_name = str(name)
            best_value = value

    return (
        best_name,
        _clean_number(best_value),
    )


# =====================================================================
# BUSINESS KPI CALCULATION
# =====================================================================

def calculate_business_metrics(
    source_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build Business Intelligence KPIs from exactly ONE selected dataset
    per dataset type.

    No same-category aggregation occurs.
    """

    source_results = _normalise_source_results(
        source_results
    )

    metrics: Dict[str, Any] = {}
    metric_sources: Dict[str, Optional[str]] = {}

    # =================================================================
    # SALES
    # =================================================================

    sales_metric_map = {
        "total_sales": ["total_sales"],
        "total_orders": ["total_orders"],
        "units_sold": ["units_sold"],
        "average_order_value": [
            "average_order_value"
        ],
        "completed_order_percentage": [
            "completed_order_percentage"
        ],
        "sales_growth": [
            "sales_growth",
            "growth",
        ],
    }

    for target_key, source_keys in sales_metric_map.items():

        _copy_source_metric(
            source_results,
            "Sales",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    # =================================================================
    # REVENUE
    # =================================================================

    total_revenue = None
    revenue_source = None

    sales_revenue, sales_revenue_source = _metric_value(
        source_results,
        "Sales",
        [
            "total_sales",
            "sales",
            "sales_amount",
        ],
    )

    if sales_revenue is not None:

        total_revenue = _clean_number(
            sales_revenue
        )

        revenue_source = (
            sales_revenue_source
        )

    else:

        financial_revenue, financial_revenue_source = _metric_value(
            source_results,
            "Financial",
            [
                "total_revenue",
                "revenue",
                "sales",
                "sales_amount",
            ],
        )

        if financial_revenue is not None:

            total_revenue = _clean_number(
                financial_revenue
            )

            revenue_source = (
                financial_revenue_source
            )

        else:

            marketing_revenue, marketing_revenue_source = _metric_value(
                source_results,
                "Marketing",
                [
                    "total_sales",
                    "sales",
                    "revenue",
                ],
            )

            if marketing_revenue is not None:

                total_revenue = _clean_number(
                    marketing_revenue
                )

                revenue_source = (
                    marketing_revenue_source
                )

    _set_metric(
        metrics,
        metric_sources,
        "total_revenue",
        total_revenue,
        revenue_source,
    )

    # =================================================================
    # CUSTOMERS
    # =================================================================

    customer_metric_map = {
        "total_customers": [
            "total_customers"
        ],
        "new_customers": [
            "new_customers"
        ],
        "active_customers": [
            "active_customers"
        ],
        "repeat_customers": [
            "repeat_customers"
        ],
        "average_customer_value": [
            "average_customer_value"
        ],
        "average_orders_per_customer": [
            "average_orders_per_customer"
        ],
        "customer_growth": [
            "customer_growth",
            "growth",
        ],
    }

    for target_key, source_keys in customer_metric_map.items():

        _copy_source_metric(
            source_results,
            "Customers",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    # =================================================================
    # PRODUCTS
    # =================================================================

    _copy_source_metric(
        source_results,
        "Products",
        metrics,
        metric_sources,
        "total_products",
        [
            "total_products",
            "product_count",
        ],
    )

    # =================================================================
    # REGIONAL
    # =================================================================

    regional_metric_map = {
        "total_regions": [
            "total_regions"
        ],
        "regional_sales": [
            "regional_sales",
            "total_sales",
        ],
        "total_sales_by_region": [
            "total_sales",
            "regional_sales",
        ],
        "regional_growth": [
            "regional_growth",
            "growth",
        ],
        "total_orders_by_region": [
            "total_orders"
        ],
        "units_sold_by_region": [
            "units_sold"
        ],
        "total_profit_by_region": [
            "total_profit"
        ],
        "profit_margin_by_region": [
            "profit_margin"
        ],
    }

    for target_key, source_keys in regional_metric_map.items():

        _copy_source_metric(
            source_results,
            "Regional",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    # =================================================================
    # MARKETING
    # =================================================================

    marketing_metric_map = {
        "total_campaigns": [
            "total_campaigns"
        ],
        "total_impressions": [
            "total_impressions"
        ],
        "total_clicks": [
            "total_clicks"
        ],
        "total_conversions": [
            "total_conversions"
        ],
        "total_leads": [
            "total_leads"
        ],
        "total_marketing_cost": [
            "total_marketing_cost"
        ],
        "total_profit": [
            "total_profit"
        ],
        "average_ctr": [
            "average_ctr"
        ],
        "conversion_rate": [
            "conversion_rate"
        ],
        "cost_per_click": [
            "cost_per_click"
        ],
        "cost_per_conversion": [
            "cost_per_conversion"
        ],
        "cost_per_lead": [
            "cost_per_lead"
        ],
        "marketing_roi": [
            "roi",
            "marketing_roi",
        ],
        "marketing_roas": [
            "roas",
            "marketing_roas",
        ],
        "customers_acquired": [
            "customers_acquired"
        ],
        "average_campaign_sales": [
            "average_campaign_sales"
        ],
        "marketing_growth": [
            "marketing_growth",
            "growth",
        ],
    }

    for target_key, source_keys in marketing_metric_map.items():

        _copy_source_metric(
            source_results,
            "Marketing",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    _copy_source_metric(
        source_results,
        "Marketing",
        metrics,
        metric_sources,
        "marketing_sales",
        [
            "total_sales",
            "sales",
            "revenue",
        ],
    )

    # =================================================================
    # FINANCIAL
    # =================================================================

    financial_metric_map = {
        "total_revenue": [
            "total_revenue",
            "revenue",
            "sales",
            "sales_amount",
        ],
        "total_cost": [
            "total_cost"
        ],
        "gross_profit": [
            "gross_profit"
        ],
        "net_profit": [
            "net_profit"
        ],
        "total_expenses": [
            "total_expenses"
        ],
        "total_tax": [
            "total_tax"
        ],
        "cash_inflow": [
            "cash_inflow"
        ],
        "cash_outflow": [
            "cash_outflow"
        ],
        "net_cash_flow": [
            "net_cash_flow"
        ],
        "average_transaction_value": [
            "average_transaction_value"
        ],
        "total_transactions": [
            "total_transactions"
        ],
        "average_transaction_count": [
            "average_transaction_count"
        ],
        "profit_margin": [
            "profit_margin"
        ],
        "revenue_growth": [
            "revenue_growth",
            "growth",
        ],
        "profit_growth": [
            "profit_growth"
        ],
        "top_category": [
            "top_category"
        ],
        "top_category_value": [
            "top_category_value"
        ],
        "top_region": [
            "top_region"
        ],
        "top_region_revenue": [
            "top_region_revenue"
        ],
    }

    for target_key, source_keys in financial_metric_map.items():

        # Do not allow Financial total_revenue to overwrite the
        # Sales-derived total_revenue when Sales is available.
        if (
            target_key == "total_revenue"
            and metrics.get("total_revenue") is not None
        ):
            continue

        _copy_source_metric(
            source_results,
            "Financial",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    # =================================================================
    # RETURNS
    # =================================================================

    returns_metric_map = {
        "total_returns": [
            "total_returns"
        ],
        "returned_units": [
            "returned_units"
        ],
        "return_value": [
            "return_value"
        ],
        "return_rate": [
            "return_rate"
        ],
        "average_return_value": [
            "average_return_value"
        ],
        "average_return_units": [
            "average_return_units"
        ],
        "returning_customers": [
            "returning_customers"
        ],
        "return_growth": [
            "return_growth",
            "growth",
        ],
    }

    for target_key, source_keys in returns_metric_map.items():

        _copy_source_metric(
            source_results,
            "Returns",
            metrics,
            metric_sources,
            target_key,
            source_keys,
        )

    # =================================================================
    # TOP PRODUCT
    # =================================================================

    product_chart = _extract_first_nonempty_chart(
        source_results,
        [
            "Sales",
            "Products",
        ],
        [
            "top_products",
            "sales_by_product",
        ],
    )

    top_product, top_product_sales = _top_chart_item(
        product_chart,
        [
            "product",
            "product_name",
            "Product",
            "Product_Name",
            "Product Name",
            "name",
            "Name",
        ],
        [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],
    )

    product_source_result = (
        _available_result(
            source_results,
            "Sales",
        )
        or _available_result(
            source_results,
            "Products",
        )
    )

    product_source_type = (
        "Sales"
        if _available_result(
            source_results,
            "Sales",
        )
        else "Products"
    )

    product_source_label = _source_label(
        product_source_type,
        product_source_result,
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_product",
        top_product,
        (
            product_source_label
            if top_product is not None
            else None
        ),
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_product_sales",
        top_product_sales,
        (
            product_source_label
            if top_product_sales is not None
            else None
        ),
    )

    # =================================================================
    # TOP REGION
    # =================================================================

    regional_chart = _extract_chart(
        source_results,
        "Regional",
        "sales_by_region",
    )

    top_region, top_region_sales = _top_chart_item(
        regional_chart,
        [
            "region",
            "Region",
            "name",
            "Name",
        ],
        [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],
    )

    regional_result = _available_result(
        source_results,
        "Regional",
    )

    regional_source_label = _source_label(
        "Regional",
        regional_result,
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_region",
        top_region,
        (
            regional_source_label
            if top_region is not None
            else None
        ),
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_region_sales",
        top_region_sales,
        (
            regional_source_label
            if top_region_sales is not None
            else None
        ),
    )

    # =================================================================
    # TOP CAMPAIGN
    # =================================================================

    campaign_chart = _extract_chart(
        source_results,
        "Marketing",
        "sales_by_campaign",
    )

    top_campaign, top_campaign_sales = _top_chart_item(
        campaign_chart,
        [
            "campaign",
            "campaign_name",
            "Campaign",
            "Campaign_Name",
            "Campaign Name",
            "name",
            "Name",
        ],
        [
            "sales",
            "total_sales",
            "sales_amount",
            "revenue",
            "value",
        ],
    )

    marketing_result = _available_result(
        source_results,
        "Marketing",
    )

    marketing_source_label = _source_label(
        "Marketing",
        marketing_result,
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_campaign",
        top_campaign,
        (
            marketing_source_label
            if top_campaign is not None
            else None
        ),
    )

    _set_metric(
        metrics,
        metric_sources,
        "top_campaign_sales",
        top_campaign_sales,
        (
            marketing_source_label
            if top_campaign_sales is not None
            else None
        ),
    )

    # =================================================================
    # DERIVED BUSINESS METRICS
    # =================================================================

    revenue_per_customer, revenue_customer_source = _derive_ratio(
        _safe_number(
            metrics.get("total_revenue")
        ),
        _safe_number(
            metrics.get("total_customers")
        ),
        _source_label_for_types(
            source_results,
            [
                "Sales",
                "Financial",
                "Customers",
            ],
        ),
    )

    _set_metric(
        metrics,
        metric_sources,
        "revenue_per_customer",
        revenue_per_customer,
        revenue_customer_source,
    )

    profit_per_order, profit_order_source = _derive_ratio(
        _safe_number(
            metrics.get("net_profit")
        ),
        _safe_number(
            metrics.get("total_orders")
        ),
        _source_label_for_types(
            source_results,
            [
                "Financial",
                "Sales",
            ],
        ),
    )

    _set_metric(
        metrics,
        metric_sources,
        "profit_per_order",
        profit_per_order,
        profit_order_source,
    )

    return_value_percentage, return_percentage_source = _derive_ratio(
        _safe_number(
            metrics.get("return_value")
        ),
        _safe_number(
            metrics.get("total_revenue")
        ),
        _source_label_for_types(
            source_results,
            [
                "Returns",
                "Sales",
                "Financial",
            ],
        ),
        100.0,
    )

    _set_metric(
        metrics,
        metric_sources,
        "return_value_percentage",
        return_value_percentage,
        return_percentage_source,
    )

    marketing_spend_percentage, marketing_percentage_source = (
        _derive_ratio(
            _safe_number(
                metrics.get(
                    "total_marketing_cost"
                )
            ),
            _safe_number(
                metrics.get(
                    "total_revenue"
                )
            ),
            _source_label_for_types(
                source_results,
                [
                    "Marketing",
                    "Sales",
                    "Financial",
                ],
            ),
            100.0,
        )
    )

    _set_metric(
        metrics,
        metric_sources,
        "marketing_spend_percentage",
        marketing_spend_percentage,
        marketing_percentage_source,
    )

    # =================================================================
    # DEFENSIVE RETURN RATE
    # =================================================================

    # Keep the Returns analytics module's return_rate when it exists.

    existing_return_rate = _safe_number(
        metrics.get("return_rate")
    )

    if existing_return_rate is None:

        total_returns = _safe_number(
            metrics.get("total_returns")
        )

        total_orders = _safe_number(
            metrics.get("total_orders")
        )

        if (
            total_returns is not None
            and total_orders is not None
            and total_orders != 0
        ):

            calculated_return_rate = _clean_number(
                (
                    total_returns
                    / total_orders
                ) * 100.0
            )

            _set_metric(
                metrics,
                metric_sources,
                "return_rate",
                calculated_return_rate,
                _source_label_for_types(
                    source_results,
                    [
                        "Returns",
                        "Sales",
                    ],
                ),
            )

    # =================================================================
    # DATASET AVAILABILITY
    # =================================================================

    available_dataset_types: List[str] = []

    for dataset_type in SUPPORTED_DATASET_TYPES:

        result = _available_result(
            source_results,
            dataset_type,
        )

        if result:
            available_dataset_types.append(
                dataset_type
            )

    selected_dataset_count = len(
        available_dataset_types
    )

    metrics["available_dataset_count"] = (
        selected_dataset_count
    )

    metrics["available_dataset_types"] = (
        available_dataset_types
    )

    metrics["selected_dataset_count"] = (
        selected_dataset_count
    )

    metrics["datasets_available"] = bool(
        available_dataset_types
    )

    # =================================================================
    # SELECTED DATASET METADATA
    # =================================================================

    selected_dataset_metadata: Dict[
        str,
        Dict[str, Any],
    ] = {}

    for dataset_type in SUPPORTED_DATASET_TYPES:

        result = _available_result(
            source_results,
            dataset_type,
        )

        if not result:
            continue

        selected_dataset_metadata[
            dataset_type
        ] = {
            "dataset_id": result.get(
                "dataset_id"
            ),
            "dataset_name": (
                result.get("dataset_name")
                or result.get("name")
            ),
            "version_id": result.get(
                "version_id"
            ),
            "version_number": result.get(
                "version_number"
            ),
        }

    metrics["selected_dataset_metadata"] = (
        selected_dataset_metadata
    )

    return {
        "metrics": metrics,
        "metric_sources": metric_sources,
        "available_dataset_types": (
            available_dataset_types
        ),
        "available_dataset_count": (
            selected_dataset_count
        ),
        "selected_dataset_count": (
            selected_dataset_count
        ),
        "selected_dataset_metadata": (
            selected_dataset_metadata
        ),
    }


# =====================================================================
# BUSINESS CHART FUNCTIONS
# =====================================================================

def business_sales_trend(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Sales",
        "sales_trend",
    )


def business_revenue_trend(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    sales_data = _extract_chart(
        source_results,
        "Sales",
        "sales_trend",
    )

    if sales_data:
        return sales_data

    financial_data = _extract_chart(
        source_results,
        "Financial",
        "revenue_trend",
    )

    if financial_data:
        return financial_data

    financial_data = _extract_chart(
        source_results,
        "Financial",
        "revenue_vs_cost",
    )

    if financial_data:
        return financial_data

    return _extract_chart(
        source_results,
        "Marketing",
        "sales_trend",
    )


def business_sales_by_region(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Regional",
        "sales_by_region",
    )


def business_units_by_region(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Regional",
        "units_by_region",
    )


def business_sales_by_category(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Sales",
        "sales_by_category",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Products",
        "sales_by_category",
    )


def business_top_products(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Sales",
        "top_products",
    )

    if chart:
        return chart

    chart = _extract_chart(
        source_results,
        "Products",
        "sales_by_product",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Products",
        "top_products",
    )


def business_customer_segments(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Customers",
        "customers_by_segment",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Customers",
        "customer_segments",
    )


def business_customer_regions(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Customers",
        "customers_by_region",
    )


def business_marketing_performance(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Marketing",
        "channel_performance",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Marketing",
        "marketing_performance",
    )


def business_marketing_campaigns(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Marketing",
        "sales_by_campaign",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Marketing",
        "marketing_campaigns",
    )


def business_financial_trend(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Financial",
        "financial_trend",
    )

    if chart:
        return chart

    chart = _extract_chart(
        source_results,
        "Financial",
        "revenue_vs_cost",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Financial",
        "revenue_trend",
    )


def business_profit_by_category(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Financial",
        "profit_by_category",
    )


def business_cash_flow(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    chart = _extract_chart(
        source_results,
        "Financial",
        "cash_flow_trend",
    )

    if chart:
        return chart

    return _extract_chart(
        source_results,
        "Financial",
        "cash_flow",
    )


def business_returns_trend(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Returns",
        "returns_trend",
    )


def business_returns_by_reason(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Returns",
        "returns_by_reason",
    )


def business_returns_by_product(
    source_results: Dict[str, Any],
) -> List[Dict[str, Any]]:

    return _extract_chart(
        source_results,
        "Returns",
        "returns_by_product",
    )


# =====================================================================
# CHART DATA AGGREGATOR
# =====================================================================

def calculate_business_chart_data(
    source_results: Optional[Dict[str, Any]] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Build all charts required by the Business Intelligence template.

    Each chart comes from ONE selected dataset.

    No chart rows are merged across datasets.
    """

    source_results = _normalise_source_results(
        source_results
    )

    return {
        "sales_trend": business_sales_trend(
            source_results
        ),

        "revenue_trend": business_revenue_trend(
            source_results
        ),

        "sales_by_region": business_sales_by_region(
            source_results
        ),

        "units_by_region": business_units_by_region(
            source_results
        ),

        "sales_by_category": business_sales_by_category(
            source_results
        ),

        "top_products": business_top_products(
            source_results
        ),

        "customer_segments": business_customer_segments(
            source_results
        ),

        "customer_regions": business_customer_regions(
            source_results
        ),

        "marketing_performance": business_marketing_performance(
            source_results
        ),

        "marketing_campaigns": business_marketing_campaigns(
            source_results
        ),

        "financial_trend": business_financial_trend(
            source_results
        ),

        "profit_by_category": business_profit_by_category(
            source_results
        ),

        "cash_flow": business_cash_flow(
            source_results
        ),

        "returns_trend": business_returns_trend(
            source_results
        ),

        "returns_by_reason": business_returns_by_reason(
            source_results
        ),

        "returns_by_product": business_returns_by_product(
            source_results
        ),
    }


# =====================================================================
# CHART AVAILABILITY
# =====================================================================

BUSINESS_CHART_LABELS = {
    "sales_trend": "Business Sales Trend",
    "revenue_trend": "Revenue Trend",
    "sales_by_region": "Sales by Region",
    "units_by_region": "Units by Region",
    "sales_by_category": "Sales by Category",
    "top_products": "Top Products",
    "customer_segments": "Customer Segments",
    "customer_regions": "Customer Regions",
    "marketing_performance": "Marketing Performance",
    "marketing_campaigns": "Marketing Campaign Performance",
    "financial_trend": "Financial Performance",
    "profit_by_category": "Profit by Category",
    "cash_flow": "Cash Flow Trend",
    "returns_trend": "Returns Trend",
    "returns_by_reason": "Returns by Reason",
    "returns_by_product": "Returns by Product",
}


def get_unavailable_business_charts(
    chart_data: Dict[str, Any],
) -> List[str]:

    unavailable: List[str] = []

    for key, label in BUSINESS_CHART_LABELS.items():

        value = chart_data.get(key)

        if (
            not isinstance(value, list)
            or not value
        ):
            unavailable.append(label)

    return unavailable


# =====================================================================
# SMART BUSINESS INSIGHTS
# =====================================================================

def generate_business_insights(
    metrics: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """
    Generate descriptive Business Intelligence observations.

    Only available metrics are used.
    """

    metrics = metrics or {}

    insights: List[str] = []

    # =================================================================
    # SALES
    # =================================================================

    total_sales = _safe_number(
        metrics.get("total_sales")
    )

    total_orders = _safe_number(
        metrics.get("total_orders")
    )

    average_order_value = _safe_number(
        metrics.get("average_order_value")
    )

    if (
        total_sales is not None
        and total_orders is not None
        and total_orders > 0
    ):
        insights.append(
            "The selected Sales dataset records "
            f"{total_orders:,.0f} orders "
            f"generating {total_sales:,.2f} in sales."
        )

    if average_order_value is not None:
        insights.append(
            "The average order value in the selected "
            f"Sales dataset is {average_order_value:,.2f}."
        )

    sales_growth = _safe_number(
        metrics.get("sales_growth")
    )

    if sales_growth is not None:

        if sales_growth > 0:
            insights.append(
                "Sales increased by "
                f"{sales_growth:.2f}% compared with the "
                "preceding comparable period."
            )

        elif sales_growth < 0:
            insights.append(
                "Sales decreased by "
                f"{abs(sales_growth):.2f}% compared with the "
                "preceding comparable period."
            )

        else:
            insights.append(
                "Sales remained unchanged compared with "
                "the preceding comparable period."
            )

    # =================================================================
    # CUSTOMERS
    # =================================================================

    total_customers = _safe_number(
        metrics.get("total_customers")
    )

    active_customers = _safe_number(
        metrics.get("active_customers")
    )

    repeat_customers = _safe_number(
        metrics.get("repeat_customers")
    )

    if total_customers is not None:
        insights.append(
            "The selected Customer dataset contains "
            f"{total_customers:,.0f} recorded customers."
        )

    if (
        active_customers is not None
        and total_customers is not None
        and total_customers > 0
    ):

        active_rate = (
            active_customers
            / total_customers
        ) * 100.0

        insights.append(
            f"{active_rate:.2f}% of recorded customers "
            "are classified as active."
        )

    if (
        repeat_customers is not None
        and total_customers is not None
        and total_customers > 0
    ):

        repeat_rate = (
            repeat_customers
            / total_customers
        ) * 100.0

        insights.append(
            f"{repeat_rate:.2f}% of recorded customers "
            "are repeat customers."
        )

    # =================================================================
    # REGIONAL
    # =================================================================

    top_region = metrics.get(
        "top_region"
    )

    top_region_sales = _safe_number(
        metrics.get("top_region_sales")
    )

    if (
        top_region
        and top_region_sales is not None
    ):
        insights.append(
            f"{top_region} has the highest recorded sales "
            f"with {top_region_sales:,.2f}."
        )

    # =================================================================
    # MARKETING
    # =================================================================

    marketing_cost = _safe_number(
        metrics.get("total_marketing_cost")
    )

    marketing_roi = _safe_number(
        metrics.get("marketing_roi")
    )

    marketing_roas = _safe_number(
        metrics.get("marketing_roas")
    )

    if marketing_cost is not None:
        insights.append(
            "Recorded marketing expenditure in the "
            "selected Marketing dataset is "
            f"{marketing_cost:,.2f}."
        )

    if marketing_roi is not None:
        insights.append(
            f"Recorded marketing ROI is "
            f"{marketing_roi:.2f}%."
        )

    if marketing_roas is not None:
        insights.append(
            f"Recorded marketing ROAS is "
            f"{marketing_roas:.2f}."
        )

    # =================================================================
    # FINANCIAL
    # =================================================================

    gross_profit = _safe_number(
        metrics.get("gross_profit")
    )

    net_profit = _safe_number(
        metrics.get("net_profit")
    )

    profit_margin = _safe_number(
        metrics.get("profit_margin")
    )

    if gross_profit is not None:
        insights.append(
            f"Gross profit is "
            f"{gross_profit:,.2f}."
        )

    if net_profit is not None:
        insights.append(
            f"Net profit is "
            f"{net_profit:,.2f}."
        )

    if profit_margin is not None:
        insights.append(
            f"The recorded profit margin is "
            f"{profit_margin:.2f}%."
        )

    # =================================================================
    # CASH FLOW
    # =================================================================

    net_cash_flow = _safe_number(
        metrics.get("net_cash_flow")
    )

    if net_cash_flow is not None:

        if net_cash_flow > 0:
            insights.append(
                "Net cash flow is positive at "
                f"{net_cash_flow:,.2f}."
            )

        elif net_cash_flow < 0:
            insights.append(
                "Net cash flow is negative at "
                f"{abs(net_cash_flow):,.2f}."
            )

        else:
            insights.append(
                "Net cash flow is currently at zero."
            )

    # =================================================================
    # RETURNS
    # =================================================================

    total_returns = _safe_number(
        metrics.get("total_returns")
    )

    return_value = _safe_number(
        metrics.get("return_value")
    )

    return_rate = _safe_number(
        metrics.get("return_rate")
    )

    if total_returns is not None:
        insights.append(
            "The selected Returns dataset records "
            f"{total_returns:,.0f} returns."
        )

    if return_value is not None:
        insights.append(
            f"Recorded return value is "
            f"{return_value:,.2f}."
        )

    if return_rate is not None:
        insights.append(
            f"The calculated return rate is "
            f"{return_rate:.2f}%."
        )

    # =================================================================
    # DERIVED BUSINESS METRICS
    # =================================================================

    revenue_per_customer = _safe_number(
        metrics.get("revenue_per_customer")
    )

    if revenue_per_customer is not None:
        insights.append(
            "Revenue per recorded customer is "
            f"{revenue_per_customer:,.2f}."
        )

    profit_per_order = _safe_number(
        metrics.get("profit_per_order")
    )

    if profit_per_order is not None:
        insights.append(
            "Net profit per recorded order is "
            f"{profit_per_order:,.2f}."
        )

    marketing_spend_percentage = _safe_number(
        metrics.get(
            "marketing_spend_percentage"
        )
    )

    if marketing_spend_percentage is not None:
        insights.append(
            "Marketing expenditure represents "
            f"{marketing_spend_percentage:.2f}% of recorded "
            "business revenue."
        )

    # =================================================================
    # TOP PRODUCT
    # =================================================================

    top_product = metrics.get(
        "top_product"
    )

    top_product_sales = _safe_number(
        metrics.get("top_product_sales")
    )

    if (
        top_product
        and top_product_sales is not None
    ):
        insights.append(
            f"{top_product} is the top recorded product "
            f"with {top_product_sales:,.2f} in sales."
        )

    # =================================================================
    # TOP CAMPAIGN
    # =================================================================

    top_campaign = metrics.get(
        "top_campaign"
    )

    top_campaign_sales = _safe_number(
        metrics.get("top_campaign_sales")
    )

    if (
        top_campaign
        and top_campaign_sales is not None
    ):
        insights.append(
            f"{top_campaign} is the top recorded campaign "
            f"with {top_campaign_sales:,.2f} in sales."
        )

    return insights


# =====================================================================
# COMPATIBILITY ALIASES
# =====================================================================

business_metrics = calculate_business_metrics

business_chart_data = calculate_business_chart_data

business_insights = generate_business_insights