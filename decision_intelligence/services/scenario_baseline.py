import os
import pandas as pd


REVENUE_COLUMNS = [
    "revenue",
    "sales",
    "sales_amount",
    "sales_value",
    "total_sales",
    "total_revenue",
    "amount",
    "order_value",
    "net_sales",
]

PROFIT_COLUMNS = [
    "profit",
    "net_profit",
    "gross_profit",
    "profit_amount",
]

COST_COLUMNS = [
    "cost",
    "cost_amount",
    "total_cost",
    "expense",
    "expenses",
    "total_expense",
    "cogs",
    "cost_of_goods_sold",
]

UNIT_COLUMNS = [
    "units",
    "quantity",
    "qty",
    "units_sold",
    "quantity_sold",
]


def normalize_column_name(column):
    return (
        str(column)
        .strip()
        .lower()
        .replace(" ", "_")
        .replace("-", "_")
        .replace("/", "_")
    )


def find_column(df, candidates):
    normalized = {
        normalize_column_name(column): column
        for column in df.columns
    }

    for candidate in candidates:
        if candidate in normalized:
            return normalized[candidate]

    # Partial matching fallback
    for normalized_name, original_name in normalized.items():
        for candidate in candidates:
            if candidate in normalized_name:
                return original_name

    return None


def numeric_sum(df, column):
    if not column:
        return 0.0

    values = pd.to_numeric(
        df[column],
        errors="coerce"
    ).fillna(0)

    return float(values.sum())


def load_dataset_dataframe(dataset):
    """
    Loads the current dataset file.

    Preference:
    1. Current cleaned version
    2. Current transformed version
    3. Dataset main file
    """

    version = (
        dataset.versions
        .filter(
            is_current=True,
            version_type__in=[
                "Cleaned",
                "Transformed",
                "Validated",
            ]
        )
        .order_by("-version_number")
        .first()
    )

    file_field = version.file if version else dataset.file

    if not file_field:
        raise ValueError("Dataset file is not available.")

    file_path = file_field.path

    if not os.path.exists(file_path):
        raise FileNotFoundError(
            "Dataset file could not be found."
        )

    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".csv":
        return pd.read_csv(file_path)

    if extension in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)

    raise ValueError(
        f"Unsupported dataset format: {extension}"
    )


def calculate_real_baseline(dataset):
    """
    Detects the important business metrics from
    the selected dataset and creates a baseline
    for the What-If Simulator.
    """

    df = load_dataset_dataframe(dataset)

    if df.empty:
        raise ValueError(
            "The selected dataset contains no data."
        )

    revenue_column = find_column(
        df,
        REVENUE_COLUMNS
    )

    profit_column = find_column(
        df,
        PROFIT_COLUMNS
    )

    cost_column = find_column(
        df,
        COST_COLUMNS
    )

    units_column = find_column(
        df,
        UNIT_COLUMNS
    )

    revenue = numeric_sum(
        df,
        revenue_column
    )

    # Profit priority:
    # 1. Existing profit column
    # 2. Revenue - Cost
    if profit_column:
        profit = numeric_sum(
            df,
            profit_column
        )
    elif cost_column:
        cost = numeric_sum(
            df,
            cost_column
        )

        profit = revenue - cost
    else:
        # Conservative fallback if the dataset
        # doesn't contain profit/cost.
        profit = revenue * 0.20

    if units_column:
        units = numeric_sum(
            df,
            units_column
        )
    else:
        # If there is no quantity column,
        # use number of rows as transaction volume.
        units = float(len(df))

    if revenue < 0:
        revenue = 0.0

    if units < 0:
        units = 0.0

    return {
        "revenue": round(revenue, 2),
        "profit": round(profit, 2),
        "units": round(units, 2),

        "revenue_column": revenue_column,
        "profit_column": profit_column,
        "cost_column": cost_column,
        "units_column": units_column,

        "rows": len(df),
        "columns": len(df.columns),

        "data_source": (
            "Cleaned dataset"
            if dataset.versions.filter(
                is_current=True,
                version_type__in=[
                    "Cleaned",
                    "Transformed",
                    "Validated",
                ]
            ).exists()
            else "Original dataset"
        ),
    }