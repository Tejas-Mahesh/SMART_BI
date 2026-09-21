from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd

from data_management.models import Dataset, DatasetVersion

from analytics.services.dataset_resolver import (
    get_user_datasets,
    resolve_dataset,
)


# IMPORTANT:
# read_dataset_version_file() is the same reader used by the
# Data Management layer to read a DatasetVersion file.
#
# Adjust this import only if your project exposes that function
# from a different module.
from data_management.views import read_dataset_version_file


# ============================================================
# DATASET TYPES
# ============================================================

DASHBOARD_DATASET_TYPES = [
    "Sales",
    "Customers",
    "Products",
    "Regional",
    "Marketing",
    "Financial",
    "Returns",
]


DATASET_TYPE_LABELS = {
    "Sales": "Sales",
    "Customers": "Customers",
    "Products": "Products",
    "Regional": "Regional",
    "Marketing": "Marketing",
    "Financial": "Financial",
    "Returns": "Returns",
}


# ============================================================
# DATA CONTAINER
# ============================================================

@dataclass
class DashboardDataset:
    """
    Dataset container used by the Executive Dashboard.

    IMPORTANT
    ---------
    dataframe ALWAYS represents a Cleaned DatasetVersion.

    The Executive Dashboard intentionally does not use:

        Dataset.file

    and does not blindly use:

        DatasetVersion.is_current

    because a transformed version may later become current.

    Executive Dashboard source:

        Dataset
            ↓
        latest Cleaned DatasetVersion
            ↓
        read_dataset_version_file()
            ↓
        dataframe
    """

    dataset: Dataset
    version: DatasetVersion
    dataframe: pd.DataFrame
    dataset_type: str


# ============================================================
# SAFE DATAFRAME HELPER
# ============================================================

def _safe_dataframe(
    dataframe: Any,
) -> pd.DataFrame:
    """
    Convert an object into a safe pandas DataFrame.

    Failed conversion returns an empty DataFrame.
    """

    if dataframe is None:
        return pd.DataFrame()

    if isinstance(dataframe, pd.DataFrame):
        return dataframe.copy()

    try:
        return pd.DataFrame(dataframe)

    except Exception:
        return pd.DataFrame()


# ============================================================
# DATASET TIMESTAMP
# ============================================================

def _dataset_timestamp(
    dataset: Dataset,
) -> float:
    """
    Return the upload timestamp used for determining
    the latest uploaded dataset.

    Primary field:

        uploaded_at

    Invalid or missing timestamps return 0.
    """

    uploaded_at = getattr(
        dataset,
        "uploaded_at",
        None,
    )

    if uploaded_at is None:
        return 0.0

    try:
        return float(
            uploaded_at.timestamp()
        )

    except (
        AttributeError,
        OSError,
        OverflowError,
        ValueError,
        TypeError,
    ):
        return 0.0


# ============================================================
# DATASET SORT KEY
# ============================================================

def _dataset_sort_key(
    dataset: Dataset,
):
    """
    Deterministic dataset ordering.

    Upload timestamp is primary.

    Dataset ID is the tie-breaker.
    """

    try:
        dataset_id = int(
            getattr(
                dataset,
                "id",
                0,
            )
            or 0
        )

    except (
        TypeError,
        ValueError,
    ):
        dataset_id = 0

    return (
        _dataset_timestamp(dataset),
        dataset_id,
    )


# ============================================================
# DATASET TYPE
# ============================================================

def _get_dataset_type(
    dataset: Dataset,
) -> Optional[str]:
    """
    Safely retrieve and validate a dataset type.
    """

    dataset_type = getattr(
        dataset,
        "dataset_type",
        None,
    )

    if not dataset_type:
        return None

    dataset_type = str(
        dataset_type
    )

    if dataset_type not in DASHBOARD_DATASET_TYPES:
        return None

    return dataset_type


# ============================================================
# DATASET NAME
# ============================================================

def _get_dataset_name(
    dataset: Dataset,
    dataset_type: str,
) -> str:
    """
    Return a safe dataset name.
    """

    name = getattr(
        dataset,
        "name",
        None,
    )

    if name is None:
        return f"{dataset_type} Dataset"

    name = str(name).strip()

    if not name:
        return f"{dataset_type} Dataset"

    return name


# ============================================================
# LATEST CLEANED VERSION
# ============================================================

def get_latest_cleaned_version(
    dataset: Dataset,
) -> Optional[DatasetVersion]:
    """
    Return the latest Cleaned DatasetVersion for a dataset.

    IMPORTANT
    ---------
    This function intentionally does NOT use is_current=True.

    The Executive Dashboard must always analyze cleaned data.

    Example:

        Version 1 -> Original
        Version 2 -> Cleaned
        Version 3 -> Transformed

    Even if Version 3 is current, the Executive Dashboard
    uses Version 2 because Version 2 is the latest Cleaned
    version.
    """

    if dataset is None:
        return None

    try:

        return (
            DatasetVersion.objects
            .filter(
                dataset=dataset,
                version_type="Cleaned",
            )
            .order_by(
                "-version_number"
            )
            .first()
        )

    except Exception:
        return None


# ============================================================
# READ CLEANED DATASET
# ============================================================

def _read_cleaned_dataset(
    dataset: Dataset,
) -> tuple[
    Optional[DatasetVersion],
    pd.DataFrame,
]:
    """
    Locate and read the latest Cleaned DatasetVersion.

    Returns:

        (cleaned_version, dataframe)

    If no cleaned version exists:

        (None, empty dataframe)

    The function NEVER falls back to:

        Dataset.file
        Original DatasetVersion
        Transformed DatasetVersion
        arbitrary current version
    """

    cleaned_version = (
        get_latest_cleaned_version(
            dataset
        )
    )

    if cleaned_version is None:
        return (
            None,
            pd.DataFrame(),
        )

    if not getattr(
        cleaned_version,
        "file",
        None,
    ):
        return (
            cleaned_version,
            pd.DataFrame(),
        )

    try:

        dataframe = read_dataset_version_file(
            cleaned_version
        )

        dataframe = _safe_dataframe(
            dataframe
        )

        # ----------------------------------------------------
        # Normalize column names
        # ----------------------------------------------------

        if not dataframe.empty:

            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

        return (
            cleaned_version,
            dataframe,
        )

    except Exception:
        return (
            cleaned_version,
            pd.DataFrame(),
        )


# ============================================================
# RESOLVER ADAPTER
# ============================================================

def _resolve_dataset_with_project_resolver(
    user,
    dataset_type: str,
    dataset_id: Any = None,
):
    """
    Resolve the Dataset record through the project's existing
    dataset resolver.

    IMPORTANT
    ---------
    The resolver is used only to identify the authorized
    Dataset.

    Its returned DatasetVersion/DataFrame are NOT trusted for
    Executive Dashboard analysis.

    The dashboard explicitly loads the latest Cleaned
    DatasetVersion afterward.
    """

    if dataset_type not in DASHBOARD_DATASET_TYPES:
        return None

    try:

        return resolve_dataset(
            user=user,
            dataset_type=dataset_type,
            dataset_id=dataset_id,
        )

    except Exception:
        return None


# ============================================================
# CONVERT DATASET TO DASHBOARD DATASET
# ============================================================

def _make_dashboard_dataset(
    resolved: Any,
    dataset_type: str,
) -> Optional[DashboardDataset]:
    """
    Convert resolver output into DashboardDataset.

    The DataFrame is explicitly loaded from the latest
    Cleaned DatasetVersion.
    """

    if resolved is None:
        return None

    dataset = getattr(
        resolved,
        "dataset",
        None,
    )

    if dataset is None:
        return None

    # --------------------------------------------------------
    # Validate dataset type
    # --------------------------------------------------------

    resolved_type = _get_dataset_type(
        dataset
    )

    if resolved_type != dataset_type:
        return None

    # --------------------------------------------------------
    # IMPORTANT:
    # Ignore resolver's version/dataframe.
    #
    # We explicitly retrieve the latest Cleaned version.
    # --------------------------------------------------------

    (
        cleaned_version,
        dataframe,
    ) = _read_cleaned_dataset(
        dataset
    )

    if cleaned_version is None:
        return None

    return DashboardDataset(
        dataset=dataset,
        version=cleaned_version,
        dataframe=dataframe,
        dataset_type=dataset_type,
    )


# ============================================================
# READ / RESOLVE ONE DATASET
# ============================================================

def read_dashboard_dataset(
    user,
    dataset_type: str,
    dataset_id: Any = None,
) -> Optional[DashboardDataset]:
    """
    Resolve exactly one dataset.

    Dataset authorization/identity is delegated to the
    project's existing resolver.

    DatasetVersion selection is NOT delegated.

    The Executive Dashboard explicitly selects the latest
    Cleaned DatasetVersion.
    """

    if dataset_type not in DASHBOARD_DATASET_TYPES:
        return None

    resolved = (
        _resolve_dataset_with_project_resolver(
            user=user,
            dataset_type=dataset_type,
            dataset_id=dataset_id,
        )
    )

    return _make_dashboard_dataset(
        resolved=resolved,
        dataset_type=dataset_type,
    )


# ============================================================
# USER DATASET DISCOVERY
# ============================================================

def get_available_dashboard_datasets(
    user,
) -> List[Dataset]:
    """
    Return every active dashboard-supported dataset belonging
    to the current user.

    Multiple datasets from the same category are preserved.

    Example:

        Sales January
        Sales February
        Sales March

    are all returned.

    This function does NOT select the latest dataset.

    Dataset selection happens separately in:

        get_latest_dashboard_datasets()
    """

    datasets: List[Dataset] = []

    for dataset_type in DASHBOARD_DATASET_TYPES:

        try:

            user_datasets = get_user_datasets(
                user,
                dataset_type=dataset_type,
            )

        except Exception:
            continue

        if user_datasets is None:
            continue

        try:

            iterable_datasets = list(
                user_datasets
            )

        except Exception:
            continue

        for dataset in iterable_datasets:

            if dataset is None:
                continue

            # ------------------------------------------------
            # Only active datasets
            # ------------------------------------------------

            if not getattr(
                dataset,
                "is_active",
                True,
            ):
                continue

            # ------------------------------------------------
            # Validate dataset type
            # ------------------------------------------------

            current_type = _get_dataset_type(
                dataset
            )

            if current_type != dataset_type:
                continue

            datasets.append(
                dataset
            )

    # ========================================================
    # ORDERING
    # ========================================================

    type_order = {
        dataset_type: index
        for index, dataset_type
        in enumerate(
            DASHBOARD_DATASET_TYPES
        )
    }

    datasets.sort(
        key=lambda dataset: (
            type_order.get(
                _get_dataset_type(
                    dataset
                ),
                len(
                    DASHBOARD_DATASET_TYPES
                ),
            ),
            -_dataset_timestamp(
                dataset
            ),
            -int(
                getattr(
                    dataset,
                    "id",
                    0,
                )
                or 0
            ),
        )
    )

    return datasets


# ============================================================
# DATASET OPTIONS FOR SELECTOR
# ============================================================

def get_dashboard_dataset_options(
    user,
) -> List[Dict[str, Any]]:
    """
    Build dataset-selector options.

    First option:

        Overall Business Intelligence

    Then every actual uploaded dataset.

    Multiple datasets from the same category remain separate.
    """

    datasets = (
        get_available_dashboard_datasets(
            user
        )
    )

    options: List[
        Dict[str, Any]
    ] = []

    # ========================================================
    # OVERALL OPTION
    # ========================================================

    options.append(
        {
            "id": None,
            "dataset_id": None,
            "dataset_type": None,
            "type": None,
            "label": (
                "Overall Business Intelligence"
            ),
            "name": (
                "Overall Business Intelligence"
            ),
            "category": "Overall",
            "is_overall": True,
        }
    )

    # ========================================================
    # ACTUAL DATASETS
    # ========================================================

    for dataset in datasets:

        dataset_type = _get_dataset_type(
            dataset
        )

        if not dataset_type:
            continue

        dataset_id = getattr(
            dataset,
            "id",
            None,
        )

        if dataset_id is None:
            continue

        dataset_name = _get_dataset_name(
            dataset,
            dataset_type,
        )

        options.append(
            {
                "id": dataset_id,
                "dataset_id": dataset_id,
                "dataset_type": dataset_type,
                "type": dataset_type,
                "label": dataset_name,
                "name": dataset_name,
                "category": (
                    DATASET_TYPE_LABELS.get(
                        dataset_type,
                        dataset_type,
                    )
                ),
                "is_overall": False,
            }
        )

    return options


# ============================================================
# LATEST DATASET PER CATEGORY
# ============================================================

def get_latest_dashboard_datasets(
    user,
) -> Dict[str, DashboardDataset]:
    """
    Find the latest uploaded dataset for every available
    category.

    Example:

        Sales January
        Sales February
        Sales March

    becomes:

        Sales -> Sales March

    Then Sales March's latest Cleaned DatasetVersion is loaded.

    Missing categories are ignored.

    Dataset records are never merged.
    """

    latest_by_type: Dict[
        str,
        Dataset,
    ] = {}

    all_datasets = (
        get_available_dashboard_datasets(
            user
        )
    )

    # ========================================================
    # FIND LATEST DATASET RECORD
    # ========================================================

    for dataset in all_datasets:

        dataset_type = _get_dataset_type(
            dataset
        )

        if not dataset_type:
            continue

        existing = latest_by_type.get(
            dataset_type
        )

        if existing is None:

            latest_by_type[
                dataset_type
            ] = dataset

            continue

        if (
            _dataset_sort_key(dataset)
            >
            _dataset_sort_key(existing)
        ):

            latest_by_type[
                dataset_type
            ] = dataset

    # ========================================================
    # RESOLVE EACH LATEST DATASET
    # ========================================================

    result: Dict[
        str,
        DashboardDataset,
    ] = {}

    for dataset_type in DASHBOARD_DATASET_TYPES:

        dataset = latest_by_type.get(
            dataset_type
        )

        if dataset is None:
            continue

        dataset_id = getattr(
            dataset,
            "id",
            None,
        )

        if dataset_id is None:
            continue

        dashboard_dataset = (
            read_dashboard_dataset(
                user=user,
                dataset_type=dataset_type,
                dataset_id=dataset_id,
            )
        )

        if dashboard_dataset is None:
            continue

        # ----------------------------------------------------
        # Overall BI only includes usable cleaned data
        # ----------------------------------------------------

        if dashboard_dataset.dataframe.empty:
            continue

        result[
            dataset_type
        ] = dashboard_dataset

    return result


# ============================================================
# SPECIFIC DATASET
# ============================================================

def get_dashboard_dataset(
    user,
    dataset_id: Any,
    dataset_type: Optional[str] = None,
) -> Optional[DashboardDataset]:
    """
    Resolve exactly one explicitly selected dataset.

    If dataset_type is provided, only that category is checked.

    If dataset_type is omitted, every supported category is
    searched.

    No other dataset is included.

    The selected dataset is always loaded from its latest
    Cleaned DatasetVersion.
    """

    # ========================================================
    # VALIDATE ID
    # ========================================================

    try:

        normalized_dataset_id = int(
            dataset_id
        )

    except (
        TypeError,
        ValueError,
    ):

        return None

    if normalized_dataset_id <= 0:
        return None

    # ========================================================
    # TYPE PROVIDED
    # ========================================================

    if dataset_type:

        if dataset_type not in (
            DASHBOARD_DATASET_TYPES
        ):
            return None

        return read_dashboard_dataset(
            user=user,
            dataset_type=dataset_type,
            dataset_id=normalized_dataset_id,
        )

    # ========================================================
    # TYPE NOT PROVIDED
    # ========================================================

    for candidate_type in (
        DASHBOARD_DATASET_TYPES
    ):

        dashboard_dataset = (
            read_dashboard_dataset(
                user=user,
                dataset_type=candidate_type,
                dataset_id=normalized_dataset_id,
            )
        )

        if dashboard_dataset is not None:
            return dashboard_dataset

    return None


# ============================================================
# OVERALL BUSINESS INTELLIGENCE
# ============================================================

def build_overall_dashboard_data(
    user,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Build the data-source layer for Overall Business
    Intelligence.

    Overall mode contains the latest uploaded dataset from
    each supported category.

    For every selected Dataset record, the latest Cleaned
    DatasetVersion is loaded.

    Raw DataFrames remain independent.

    Date boundaries are stored in the returned structure for
    dashboard_metrics.py to apply.
    """

    available = (
        get_latest_dashboard_datasets(
            user
        )
    )

    datasets: Dict[
        str,
        DashboardDataset,
    ] = {}

    for dataset_type in DASHBOARD_DATASET_TYPES:

        dashboard_dataset = available.get(
            dataset_type
        )

        if dashboard_dataset is None:
            continue

        datasets[
            dataset_type
        ] = dashboard_dataset

    return {
        "mode": "overall",

        "dataset_count": len(
            datasets
        ),

        "available_types": list(
            datasets.keys()
        ),

        "datasets": datasets,

        "selected": None,

        # ----------------------------------------------------
        # Availability
        # ----------------------------------------------------

        "has_sales": (
            "Sales" in datasets
        ),

        "has_customers": (
            "Customers" in datasets
        ),

        "has_products": (
            "Products" in datasets
        ),

        "has_regional": (
            "Regional" in datasets
        ),

        "has_marketing": (
            "Marketing" in datasets
        ),

        "has_financial": (
            "Financial" in datasets
        ),

        "has_returns": (
            "Returns" in datasets
        ),

        # ----------------------------------------------------
        # Date range
        # ----------------------------------------------------

        "from_date": from_date,

        "to_date": to_date,

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        "error": None,

        # ----------------------------------------------------
        # Warning
        # ----------------------------------------------------

        "warning": None,
    }


# ============================================================
# SINGLE DATASET BUSINESS INTELLIGENCE
# ============================================================

def build_selected_dashboard_data(
    user,
    dataset_id: Any,
    dataset_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Optional[Dict[str, Any]]:
    """
    Build the data-source layer for Single Dataset
    Intelligence.

    Exactly one dataset is returned.

    The selected dataset's latest Cleaned DatasetVersion is
    used.

    No other dataset category is included.
    """

    dashboard_dataset = (
        get_dashboard_dataset(
            user=user,
            dataset_id=dataset_id,
            dataset_type=dataset_type,
        )
    )

    if dashboard_dataset is None:
        return None

    selected_type = (
        dashboard_dataset.dataset_type
    )

    # --------------------------------------------------------
    # Warn if cleaned data exists but could not be loaded
    # --------------------------------------------------------

    warning = None

    if dashboard_dataset.dataframe.empty:

        warning = (
            "The selected dataset has a Cleaned "
            "DatasetVersion, but its data could not "
            "be loaded."
        )

    return {
        "mode": "selected",

        "dataset_count": 1,

        "available_types": [
            selected_type
        ],

        "datasets": {
            selected_type: dashboard_dataset
        },

        "selected": dashboard_dataset,

        # ----------------------------------------------------
        # Availability
        # ----------------------------------------------------

        "has_sales": (
            selected_type == "Sales"
        ),

        "has_customers": (
            selected_type == "Customers"
        ),

        "has_products": (
            selected_type == "Products"
        ),

        "has_regional": (
            selected_type == "Regional"
        ),

        "has_marketing": (
            selected_type == "Marketing"
        ),

        "has_financial": (
            selected_type == "Financial"
        ),

        "has_returns": (
            selected_type == "Returns"
        ),

        # ----------------------------------------------------
        # Date range
        # ----------------------------------------------------

        "from_date": from_date,

        "to_date": to_date,

        # ----------------------------------------------------
        # Error
        # ----------------------------------------------------

        "error": None,

        # ----------------------------------------------------
        # Warning
        # ----------------------------------------------------

        "warning": warning,
    }


# ============================================================
# PUBLIC EXECUTIVE DASHBOARD RESOLVER
# ============================================================

def resolve_executive_dashboard(
    user,
    dataset_id: Any = None,
    dataset_type: Optional[str] = None,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Main Executive Dashboard data-source resolver.

    ========================================================
    MODE 1
    ========================================================

    No dataset selected.

        Overall Business Intelligence

    Latest uploaded dataset from each available category is
    selected.

    For each selected Dataset:

        latest Cleaned DatasetVersion

    is loaded.

    ========================================================
    MODE 2
    ========================================================

    Dataset selected.

        Single Dataset Intelligence

    Exactly the selected dataset is returned.

    Its latest Cleaned DatasetVersion is loaded.

    ========================================================
    IMPORTANT
    ========================================================

    This function DOES NOT calculate:

        KPIs
        charts
        trends
        forecasts
        anomalies
        risks
        insights
        recommendations

    Those belong exclusively to:

        analytics/metrics/dashboard_metrics.py

    ========================================================
    CLEAN DATA GUARANTEE
    ========================================================

    Executive Dashboard data source:

        Dataset
            ↓
        latest Cleaned DatasetVersion
            ↓
        read_dataset_version_file()
            ↓
        dashboard_metrics.py
    """

    # ========================================================
    # OVERALL MODE
    # ========================================================

    if dataset_id in (
        None,
        "",
        "overall",
        "all",
    ):

        return build_overall_dashboard_data(
            user=user,
            from_date=from_date,
            to_date=to_date,
        )

    # ========================================================
    # SELECTED DATASET MODE
    # ========================================================

    selected_dashboard = (
        build_selected_dashboard_data(
            user=user,
            dataset_id=dataset_id,
            dataset_type=dataset_type,
            from_date=from_date,
            to_date=to_date,
        )
    )

    if selected_dashboard is not None:
        return selected_dashboard

    # ========================================================
    # INVALID / UNAVAILABLE DATASET
    # ========================================================

    return {
        "mode": "selected",

        "dataset_count": 0,

        "available_types": [],

        "datasets": {},

        "selected": None,

        "has_sales": False,

        "has_customers": False,

        "has_products": False,

        "has_regional": False,

        "has_marketing": False,

        "has_financial": False,

        "has_returns": False,

        "from_date": from_date,

        "to_date": to_date,

        "error": (
            "The selected dataset is unavailable "
            "or does not have a Cleaned DatasetVersion."
        ),

        "warning": None,
    }


# ============================================================
# DASHBOARD DATASET METADATA
# ============================================================

def get_dashboard_dataset_metadata(
    dashboard_dataset: Optional[
        DashboardDataset
    ],
) -> Dict[str, Any]:
    """
    Return safe metadata for one dashboard dataset.

    The returned version should always be:

        version_type == "Cleaned"
    """

    if dashboard_dataset is None:
        return {}

    dataset = (
        dashboard_dataset.dataset
    )

    version = (
        dashboard_dataset.version
    )

    dataframe = _safe_dataframe(
        dashboard_dataset.dataframe
    )

    return {
        "dataset_id": getattr(
            dataset,
            "id",
            None,
        ),

        "dataset_name": _get_dataset_name(
            dataset,
            dashboard_dataset.dataset_type,
        ),

        "dataset_type": (
            dashboard_dataset.dataset_type
        ),

        "version_id": getattr(
            version,
            "id",
            None,
        ),

        "version_number": getattr(
            version,
            "version_number",
            None,
        ),

        "version_type": getattr(
            version,
            "version_type",
            None,
        ),

        "is_cleaned": (
            getattr(
                version,
                "version_type",
                None,
            )
            == "Cleaned"
        ),

        "row_count": int(
            len(dataframe)
        ),

        "column_count": int(
            len(dataframe.columns)
        ),

        "columns": [
            str(column)
            for column in dataframe.columns
        ],
    }


# ============================================================
# OVERALL DASHBOARD METADATA
# ============================================================

def get_overall_dashboard_metadata(
    dashboard_data: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """
    Return metadata for every dataset participating in Overall
    Business Intelligence.
    """

    datasets = dashboard_data.get(
        "datasets",
        {},
    )

    if not isinstance(
        datasets,
        dict,
    ):
        return []

    metadata: List[
        Dict[str, Any]
    ] = []

    for dataset_type in (
        DASHBOARD_DATASET_TYPES
    ):

        dashboard_dataset = (
            datasets.get(
                dataset_type
            )
        )

        if dashboard_dataset is None:
            continue

        metadata.append(
            get_dashboard_dataset_metadata(
                dashboard_dataset
            )
        )

    return metadata


# ============================================================
# SELECTED DASHBOARD METADATA
# ============================================================

def get_selected_dashboard_metadata(
    dashboard_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return metadata for the explicitly selected dataset.
    """

    selected = dashboard_data.get(
        "selected"
    )

    if selected is None:
        return {}

    return get_dashboard_dataset_metadata(
        selected
    )


# ============================================================
# DASHBOARD AVAILABILITY SUMMARY
# ============================================================

def get_dashboard_availability(
    dashboard_data: Dict[str, Any],
) -> Dict[str, bool]:
    """
    Return dataset-category availability flags.
    """

    return {
        "Sales": bool(
            dashboard_data.get(
                "has_sales",
                False,
            )
        ),

        "Customers": bool(
            dashboard_data.get(
                "has_customers",
                False,
            )
        ),

        "Products": bool(
            dashboard_data.get(
                "has_products",
                False,
            )
        ),

        "Regional": bool(
            dashboard_data.get(
                "has_regional",
                False,
            )
        ),

        "Marketing": bool(
            dashboard_data.get(
                "has_marketing",
                False,
            )
        ),

        "Financial": bool(
            dashboard_data.get(
                "has_financial",
                False,
            )
        ),

        "Returns": bool(
            dashboard_data.get(
                "has_returns",
                False,
            )
        ),
    }


# ============================================================
# DATE RANGE INFORMATION
# ============================================================

def get_dashboard_date_range(
    dashboard_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Return the date range passed into the dashboard resolver.

    Metrics can use these values when filtering their
    DataFrames.
    """

    return {
        "from_date": dashboard_data.get(
            "from_date"
        ),

        "to_date": dashboard_data.get(
            "to_date"
        ),

        "has_from_date": (
            dashboard_data.get(
                "from_date"
            )
            is not None
        ),

        "has_to_date": (
            dashboard_data.get(
                "to_date"
            )
            is not None
        ),
    }


# ============================================================
# CLEANED DATA SOURCE VALIDATION
# ============================================================

def validate_dashboard_cleaned_source(
    dashboard_dataset: Optional[
        DashboardDataset
    ],
) -> Dict[str, Any]:
    """
    Validate that a DashboardDataset really comes from a
    Cleaned DatasetVersion.

    This is useful for debugging and for protecting the
    Executive Dashboard against accidental use of another
    DatasetVersion type.
    """

    if dashboard_dataset is None:

        return {
            "valid": False,
            "reason": (
                "No dashboard dataset was supplied."
            ),
            "version_type": None,
            "version_id": None,
        }

    version = (
        dashboard_dataset.version
    )

    version_type = getattr(
        version,
        "version_type",
        None,
    )

    version_id = getattr(
        version,
        "id",
        None,
    )

    dataframe = _safe_dataframe(
        dashboard_dataset.dataframe
    )

    if version_type != "Cleaned":

        return {
            "valid": False,
            "reason": (
                "Executive Dashboard data must "
                "come from a Cleaned DatasetVersion."
            ),
            "version_type": version_type,
            "version_id": version_id,
        }

    if dataframe.empty:

        return {
            "valid": False,
            "reason": (
                "The Cleaned DatasetVersion contains "
                "no readable data."
            ),
            "version_type": version_type,
            "version_id": version_id,
        }

    return {
        "valid": True,
        "reason": (
            "Executive Dashboard is using the "
            "Cleaned DatasetVersion."
        ),
        "version_type": version_type,
        "version_id": version_id,
    }


# ============================================================
# END OF dashboard_service.py
# ============================================================