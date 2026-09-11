import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from data_management.models import Dataset, DatasetVersion


def user_is_approved(request):
    return (
        request.user.is_authenticated
        and request.user.approval_status == "Approved"
    )


def get_cleaned_version(dataset):
    """
    Return the current cleaned version.
    """

    version = DatasetVersion.objects.filter(
        dataset=dataset,
        version_type="Cleaned",
        is_current=True
    ).first()

    if version:
        return version

    return DatasetVersion.objects.filter(
        dataset=dataset,
        version_type="Cleaned"
    ).order_by("-version_number").first()


def read_dataset(version, dataset):
    """
    Read the cleaned dataset into pandas.
    """

    file_to_read = None

    if version and version.file:
        file_to_read = version.file

    elif dataset.file:
        file_to_read = dataset.file

    if not file_to_read:
        return None

    filename = ""

    if version:
        filename = version.file_name or ""

    if not filename:
        filename = (
            dataset.original_filename
            or dataset.file.name
        )

    filename = filename.lower()

    try:

        file_to_read.open("rb")

        if filename.endswith(".csv"):

            dataframe = pd.read_csv(file_to_read)

        elif filename.endswith(".xlsx"):

            dataframe = pd.read_excel(
                file_to_read,
                engine="openpyxl"
            )

        elif filename.endswith(".xls"):

            dataframe = pd.read_excel(file_to_read)

        else:

            file_to_read.close()
            return None

        file_to_read.close()

        return dataframe

    except Exception:

        try:
            file_to_read.close()
        except Exception:
            pass

        return None


def find_column(dataframe, possible_names):
    """
    Find a dataframe column using flexible naming.
    """

    normalized = {
        str(column).strip().lower().replace(" ", "_"): column
        for column in dataframe.columns
    }

    for name in possible_names:

        key = (
            name.strip()
            .lower()
            .replace(" ", "_")
        )

        if key in normalized:
            return normalized[key]

    return None


@login_required
def business_intelligence(request):

    if not user_is_approved(request):

        return redirect("accounts:login")

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    ).order_by("-uploaded_at")

    if not datasets.exists():

        messages.warning(
            request,
            "Upload a dataset before opening Business Analytics."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # Select dataset
    # ---------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    if dataset_id:

        dataset = datasets.filter(
            id=dataset_id
        ).first()

    else:

        dataset = datasets.first()

    if not dataset:

        messages.error(
            request,
            "Selected dataset was not found."
        )

        return redirect(
            "analytics:business_intelligence"
        )

    # ---------------------------------------------------------
    # Get cleaned version
    # ---------------------------------------------------------

    cleaned_version = get_cleaned_version(dataset)

    if not cleaned_version:

        messages.warning(
            request,
            "This dataset does not have a cleaned version yet."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # Read cleaned data
    # ---------------------------------------------------------

    dataframe = read_dataset(
        cleaned_version,
        dataset
    )

    if dataframe is None or dataframe.empty:

        messages.error(
            request,
            "The cleaned dataset could not be analyzed."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # Clean column names
    # ---------------------------------------------------------

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    # ---------------------------------------------------------
    # Detect important columns
    # ---------------------------------------------------------

    date_column = find_column(
        dataframe,
        [
            "date",
            "order_date",
            "sales_date",
            "transaction_date",
            "created_at"
        ]
    )

    sales_column = find_column(
        dataframe,
        [
            "sales",
            "revenue",
            "amount",
            "total_sales",
            "total_revenue"
        ]
    )

    quantity_column = find_column(
        dataframe,
        [
            "quantity",
            "qty",
            "units",
            "units_sold"
        ]
    )

    region_column = find_column(
        dataframe,
        [
            "region",
            "area",
            "city",
            "location"
        ]
    )

    product_column = find_column(
        dataframe,
        [
            "product",
            "product_name",
            "item",
            "item_name"
        ]
    )

    # ---------------------------------------------------------
    # Convert numeric columns
    # ---------------------------------------------------------

    if sales_column:

        dataframe[sales_column] = pd.to_numeric(
            dataframe[sales_column],
            errors="coerce"
        ).fillna(0)

    if quantity_column:

        dataframe[quantity_column] = pd.to_numeric(
            dataframe[quantity_column],
            errors="coerce"
        ).fillna(0)

    # ---------------------------------------------------------
    # Date conversion
    # ---------------------------------------------------------

    if date_column:

        dataframe[date_column] = pd.to_datetime(
            dataframe[date_column],
            errors="coerce"
        )

        dataframe = dataframe.dropna(
            subset=[date_column]
        )

        dataframe = dataframe.sort_values(
            date_column
        )

    # ---------------------------------------------------------
    # KPI calculations
    # ---------------------------------------------------------

    total_revenue = 0

    if sales_column:

        total_revenue = float(
            dataframe[sales_column].sum()
        )

    total_orders = len(dataframe)

    total_quantity = 0

    if quantity_column:

        total_quantity = float(
            dataframe[quantity_column].sum()
        )

    average_order_value = (
        total_revenue / total_orders
        if total_orders > 0
        else 0
    )

    # ---------------------------------------------------------
    # Revenue trend
    # ---------------------------------------------------------

    revenue_labels = []
    revenue_values = []

    if date_column and sales_column:

        trend = (
            dataframe
            .set_index(date_column)[sales_column]
            .resample("ME")
            .sum()
        )

        revenue_labels = [
            date.strftime("%b %Y")
            for date in trend.index
        ]

        revenue_values = [
            round(float(value), 2)
            for value in trend.values
        ]

    # ---------------------------------------------------------
    # Revenue by region
    # ---------------------------------------------------------

    region_labels = []
    region_values = []

    if region_column and sales_column:

        region_data = (
            dataframe
            .groupby(region_column)[sales_column]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        region_labels = [
            str(value)
            for value in region_data.index
        ]

        region_values = [
            round(float(value), 2)
            for value in region_data.values
        ]

    # ---------------------------------------------------------
    # Top products
    # ---------------------------------------------------------

    product_labels = []
    product_values = []

    if product_column and sales_column:

        product_data = (
            dataframe
            .groupby(product_column)[sales_column]
            .sum()
            .sort_values(ascending=False)
            .head(10)
        )

        product_labels = [
            str(value)
            for value in product_data.index
        ]

        product_values = [
            round(float(value), 2)
            for value in product_data.values
        ]

    # ---------------------------------------------------------
    # Growth calculation
    # ---------------------------------------------------------

    growth_percentage = 0

    if (
        date_column
        and sales_column
        and len(revenue_values) >= 2
    ):

        previous = revenue_values[-2]
        current = revenue_values[-1]

        if previous != 0:

            growth_percentage = (
                (current - previous)
                / previous
            ) * 100

    # ---------------------------------------------------------
    # Executive summary
    # ---------------------------------------------------------

    summary = []

    if sales_column:

        summary.append(
            f"Total revenue generated is ₹{total_revenue:,.2f}."
        )

    if region_labels:

        summary.append(
            f"{region_labels[0]} is currently the "
            f"highest-revenue region."
        )

    if product_labels:

        summary.append(
            f"{product_labels[0]} is the "
            f"top-performing product by revenue."
        )

    if growth_percentage > 0:

        summary.append(
            f"Revenue increased by "
            f"{growth_percentage:.1f}% compared with "
            f"the previous period."
        )

    elif growth_percentage < 0:

        summary.append(
            f"Revenue decreased by "
            f"{abs(growth_percentage):.1f}% compared with "
            f"the previous period."
        )

    else:

        summary.append(
            "Revenue growth could not be determined "
            "from the available data."
        )

    context = {

        "dataset": dataset,

        "datasets": datasets,

        "cleaned_version": cleaned_version,

        "total_revenue": total_revenue,

        "total_orders": total_orders,

        "total_quantity": total_quantity,

        "average_order_value": average_order_value,

        "growth_percentage": growth_percentage,

        "revenue_labels": revenue_labels,

        "revenue_values": revenue_values,

        "region_labels": region_labels,

        "region_values": region_values,

        "product_labels": product_labels,

        "product_values": product_values,

        "summary": summary,

        "date_column": date_column,

        "sales_column": sales_column,

        "quantity_column": quantity_column,

        "region_column": region_column,

        "product_column": product_column,

    }

    return render(
        request,
        "analytics/business_intelligence.html",
        context
    )