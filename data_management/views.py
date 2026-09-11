import os

import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db.models import Prefetch
from django.http import HttpResponse
from django.shortcuts import redirect, render

from .forms import DatasetUploadForm
from .models import Dataset, DatasetVersion, DatasetActivity


# ============================================================
# COMMON APPROVAL CHECK
# ============================================================

def user_is_approved(request):
    return (
        request.user.is_authenticated
        and request.user.approval_status == "Approved"
    )


# ============================================================
# COMMON DATASET READER
# ============================================================

def read_dataset_file(dataset):
    """
    Read a Dataset file using pandas.

    Supports:
        CSV
        XLS
        XLSX
    """

    if not dataset.file:
        raise ValueError("Dataset file is missing.")

    filename = (
        dataset.original_filename
        or dataset.file.name
        or ""
    ).lower()

    file_path = dataset.file.path

    if filename.endswith(".csv"):

        return pd.read_csv(file_path)

    elif filename.endswith(".xls"):

        return pd.read_excel(file_path)

    elif filename.endswith(".xlsx"):

        return pd.read_excel(file_path)

    raise ValueError(
        "Unsupported dataset format. "
        "Only CSV, XLS and XLSX files are supported."
    )


# ============================================================
# COMMON QUALITY SCORE
# ============================================================

def calculate_quality_score(
    dataframe,
    missing_values=None,
    duplicate_rows=None
):
    """
    Calculate Smart BI data quality score.

    Score considers:
        - Missing values
        - Duplicate rows
    """

    total_rows = len(dataframe)
    total_columns = len(dataframe.columns)

    if missing_values is None:
        missing_values = int(
            dataframe.isnull().sum().sum()
        )

    if duplicate_rows is None:
        duplicate_rows = int(
            dataframe.duplicated().sum()
        )

    if total_rows == 0:
        return 0

    total_cells = max(
        total_rows * max(total_columns, 1),
        1
    )

    missing_penalty = (
        missing_values / total_cells
    ) * 100

    duplicate_penalty = (
        duplicate_rows / max(total_rows, 1)
    ) * 100

    score = max(
        0,
        100
        - missing_penalty
        - duplicate_penalty
    )

    return round(score, 2)


# ============================================================
# CREATE ORIGINAL VERSION
# ============================================================

def create_original_dataset_version(dataset):

    try:

        existing_version = (
            DatasetVersion.objects
            .filter(
                dataset=dataset,
                version_number=1
            )
            .first()
        )

        if existing_version:
            return existing_version

        # Make sure there is no other current version.
        DatasetVersion.objects.filter(
            dataset=dataset,
            is_current=True
        ).update(
            is_current=False
        )

        version = DatasetVersion.objects.create(

            dataset=dataset,

            version_number=1,

            version_type="Original",

            file=dataset.file,

            file_name=(
                dataset.original_filename
                or os.path.basename(
                    dataset.file.name
                )
            ),

            file_size=dataset.file_size,

            total_rows=dataset.total_rows,

            total_columns=dataset.total_columns,

            missing_values=dataset.missing_values,

            duplicate_rows=dataset.duplicate_rows,

            quality_score=dataset.quality_score,

            notes=(
                "Original dataset uploaded by the user."
            ),

            is_current=True
        )

        return version

    except Exception:
        return None


# ============================================================
# CREATE CLEANED DATASET VERSION
# ============================================================

def create_cleaned_dataset_version(
    dataset,
    cleaned_dataframe,
    missing_before,
    missing_after,
    duplicates_before,
    duplicates_after,
):
    """
    Save the automatically cleaned dataframe as a real
    DatasetVersion.

    Version 1 = Original
    Version 2 = Cleaned
    """

    try:

        # ----------------------------------------------------
        # Determine next version number
        # ----------------------------------------------------

        latest_version = (
            DatasetVersion.objects
            .filter(
                dataset=dataset
            )
            .order_by(
                "-version_number"
            )
            .first()
        )

        if latest_version:

            next_version = (
                latest_version.version_number
                + 1
            )

        else:

            next_version = 1

        # ----------------------------------------------------
        # Calculate cleaned statistics
        # ----------------------------------------------------

        cleaned_rows = len(
            cleaned_dataframe
        )

        cleaned_columns = len(
            cleaned_dataframe.columns
        )

        cleaned_quality_score = (
            calculate_quality_score(
                cleaned_dataframe,
                missing_after,
                duplicates_after
            )
        )

        # ----------------------------------------------------
        # Convert cleaned dataframe to CSV
        # ----------------------------------------------------

        csv_content = (
            cleaned_dataframe
            .to_csv(index=False)
        )

        # ----------------------------------------------------
        # Safe filename
        # ----------------------------------------------------

        original_name = (
            dataset.original_filename
            or dataset.name
            or "dataset"
        )

        base_name = os.path.splitext(
            os.path.basename(
                original_name
            )
        )[0]

        cleaned_filename = (
            f"{base_name}_cleaned_v"
            f"{next_version}.csv"
        )

        # ----------------------------------------------------
        # Make previous current version inactive
        # ----------------------------------------------------

        DatasetVersion.objects.filter(
            dataset=dataset,
            is_current=True
        ).update(
            is_current=False
        )

        # ----------------------------------------------------
        # Create version
        # ----------------------------------------------------

        version = DatasetVersion(
            dataset=dataset,

            version_number=next_version,

            version_type="Cleaned",

            file_name=cleaned_filename,

            total_rows=cleaned_rows,

            total_columns=cleaned_columns,

            missing_values=missing_after,

            duplicate_rows=duplicates_after,

            quality_score=cleaned_quality_score,

            notes=(
                "Automatically cleaned by Smart BI. "
                f"Missing values changed from "
                f"{missing_before} to "
                f"{missing_after}. "
                f"Duplicate rows changed from "
                f"{duplicates_before} to "
                f"{duplicates_after}."
            ),

            is_current=True,
        )

        # ----------------------------------------------------
        # Save physical cleaned file
        # ----------------------------------------------------

        version.file.save(
            cleaned_filename,
            ContentFile(
                csv_content.encode("utf-8")
            ),
            save=False
        )

        version.file_size = (
            version.file.size
            if version.file
            else len(
                csv_content.encode("utf-8")
            )
        )

        version.save()

        # ----------------------------------------------------
        # Update main Dataset
        # ----------------------------------------------------

        dataset.total_rows = (
            cleaned_rows
        )

        dataset.total_columns = (
            cleaned_columns
        )

        dataset.missing_values = (
            missing_after
        )

        dataset.duplicate_rows = (
            duplicates_after
        )

        dataset.quality_score = (
            cleaned_quality_score
        )

        dataset.save(
            update_fields=[
                "total_rows",
                "total_columns",
                "missing_values",
                "duplicate_rows",
                "quality_score",
                "updated_at",
            ]
        )

        return version

    except Exception as error:

        print(
            "Unable to create cleaned dataset version:",
            error
        )

        return None


# ============================================================
# UPLOAD DATASET
# ============================================================

@login_required
def upload_dataset(request):

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

    if request.method == "POST":

        form = DatasetUploadForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            dataset = form.save(
                commit=False
            )

            dataset.owner = request.user

            uploaded_file = request.FILES.get(
                "file"
            )

            if uploaded_file is None:

                messages.error(
                    request,
                    "Please select a dataset file."
                )

                return render(
                    request,
                    "data_management/upload.html",
                    {
                        "form": form
                    }
                )

            dataset.original_filename = (
                uploaded_file.name
            )

            dataset.file_size = (
                uploaded_file.size
            )

            try:

                # =================================================
                # 01. READ DATASET
                # =================================================

                filename = (
                    uploaded_file.name.lower()
                )

                uploaded_file.seek(0)

                if filename.endswith(".csv"):

                    dataframe = pd.read_csv(
                        uploaded_file
                    )

                elif filename.endswith(
                    (".xls", ".xlsx")
                ):

                    dataframe = pd.read_excel(
                        uploaded_file
                    )

                else:

                    messages.error(
                        request,
                        "Unsupported file format."
                    )

                    return render(
                        request,
                        "data_management/upload.html",
                        {
                            "form": form
                        }
                    )

                # =================================================
                # 02. BASIC DATA ANALYSIS
                # =================================================

                total_rows = len(
                    dataframe
                )

                total_columns = len(
                    dataframe.columns
                )

                missing_values = int(
                    dataframe
                    .isnull()
                    .sum()
                    .sum()
                )

                duplicate_rows = int(
                    dataframe
                    .duplicated()
                    .sum()
                )

                # =================================================
                # 03. QUALITY SCORE
                # =================================================

                quality_score = (
                    calculate_quality_score(
                        dataframe,
                        missing_values,
                        duplicate_rows
                    )
                )

                # =================================================
                # 04. SAVE DATASET
                # =================================================

                dataset.total_rows = (
                    total_rows
                )

                dataset.total_columns = (
                    total_columns
                )

                dataset.missing_values = (
                    missing_values
                )

                dataset.duplicate_rows = (
                    duplicate_rows
                )

                dataset.quality_score = (
                    quality_score
                )

                dataset.save()

                # =================================================
                # 05. REMOVE OLD ACTIVITIES
                # =================================================

                DatasetActivity.objects.filter(
                    dataset=dataset
                ).delete()

                # =================================================
                # 06. UPLOADED
                # =================================================

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Uploaded",

                    status="Success",

                    title=(
                        "Dataset uploaded successfully"
                    ),

                    description=(
                        f"{dataset.original_filename} "
                        f"was uploaded successfully."
                    ),

                    details={

                        "filename":
                            dataset.original_filename,

                        "file_size":
                            dataset.file_size,

                        "rows":
                            total_rows,

                        "columns":
                            total_columns,
                    }
                )

                # =================================================
                # 07. VALIDATION
                # =================================================

                column_names = [
                    str(column).strip()
                    for column
                    in dataframe.columns
                ]

                validation_issues = []

                if total_rows == 0:

                    validation_issues.append(
                        "Dataset contains no records."
                    )

                if total_columns == 0:

                    validation_issues.append(
                        "Dataset contains no columns."
                    )

                if len(column_names) != len(
                    set(column_names)
                ):

                    validation_issues.append(
                        "Duplicate column names detected."
                    )

                validation_status = (
                    "Warning"
                    if validation_issues
                    else "Success"
                )

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Validated",

                    status=validation_status,

                    title=(
                        "Dataset structure validated"
                    ),

                    description=(
                        "Smart BI checked the file "
                        "structure, columns and records."
                    ),

                    details={

                        "rows":
                            total_rows,

                        "columns":
                            total_columns,

                        "issues":
                            validation_issues,

                        "column_names":
                            column_names,
                    }
                )

                # =================================================
                # 08. PROFILING
                # =================================================

                numeric_columns = [
                    str(column)
                    for column
                    in dataframe
                    .select_dtypes(
                        include="number"
                    )
                    .columns
                ]

                categorical_columns = [
                    str(column)
                    for column
                    in dataframe
                    .select_dtypes(
                        include=[
                            "object",
                            "category"
                        ]
                    )
                    .columns
                ]

                datetime_columns = []

                for column in dataframe.columns:

                    if pd.api.types.is_datetime64_any_dtype(
                        dataframe[column]
                    ):

                        datetime_columns.append(
                            str(column)
                        )

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Profiled",

                    status="Success",

                    title=(
                        "Dataset profile generated"
                    ),

                    description=(
                        "Smart BI analyzed column "
                        "types, numeric fields, "
                        "categorical fields and "
                        "dataset structure."
                    ),

                    details={

                        "numeric_columns":
                            numeric_columns,

                        "categorical_columns":
                            categorical_columns,

                        "datetime_columns":
                            datetime_columns,

                        "unique_values": {
                            str(column):
                            int(
                                dataframe[column]
                                .nunique(
                                    dropna=True
                                )
                            )
                            for column
                            in dataframe.columns
                        },
                    }
                )

                # =================================================
                # 09. QUALITY CHECK
                # =================================================

                quality_status = (
                    "Success"
                    if quality_score >= 70
                    else "Warning"
                )

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Quality Checked",

                    status=quality_status,

                    title=(
                        "Data quality assessment completed"
                    ),

                    description=(
                        "Smart BI calculated the "
                        "initial dataset quality score."
                    ),

                    details={

                        "quality_score":
                            quality_score,

                        "missing_values":
                            missing_values,

                        "duplicate_rows":
                            duplicate_rows,

                        "total_rows":
                            total_rows,
                    }
                )

                # =================================================
                # 10. AUTOMATIC CLEANING
                # =================================================

                cleaned_dataframe = (
                    dataframe.copy()
                )

                cleaned_missing = int(
                    cleaned_dataframe
                    .isnull()
                    .sum()
                    .sum()
                )

                cleaned_duplicates = int(
                    cleaned_dataframe
                    .duplicated()
                    .sum()
                )

                rows_before_cleaning = (
                    len(cleaned_dataframe)
                )

                # -------------------------------------------------
                # Remove completely empty rows
                # -------------------------------------------------

                empty_rows_removed = int(
                    cleaned_dataframe
                    .isnull()
                    .all(axis=1)
                    .sum()
                )

                if empty_rows_removed > 0:

                    cleaned_dataframe = (
                        cleaned_dataframe
                        .dropna(how="all")
                    )

                # -------------------------------------------------
                # Remove duplicate rows
                # -------------------------------------------------

                duplicate_rows_removed = int(
                    cleaned_dataframe
                    .duplicated()
                    .sum()
                )

                if duplicate_rows_removed > 0:

                    cleaned_dataframe = (
                        cleaned_dataframe
                        .drop_duplicates()
                    )

                # -------------------------------------------------
                # Fill numeric missing values
                # -------------------------------------------------

                numeric_values_filled = 0

                numeric_columns_cleaning = (
                    cleaned_dataframe
                    .select_dtypes(
                        include="number"
                    )
                    .columns
                )

                for column in (
                    numeric_columns_cleaning
                ):

                    missing_count = int(
                        cleaned_dataframe[column]
                        .isnull()
                        .sum()
                    )

                    if missing_count > 0:

                        median_value = (
                            cleaned_dataframe[column]
                            .median()
                        )

                        if pd.notna(
                            median_value
                        ):

                            cleaned_dataframe[
                                column
                            ] = (
                                cleaned_dataframe[
                                    column
                                ]
                                .fillna(
                                    median_value
                                )
                            )

                            numeric_values_filled += (
                                missing_count
                            )

                # -------------------------------------------------
                # Fill categorical missing values
                # -------------------------------------------------

                categorical_values_filled = 0

                categorical_columns_cleaning = (
                    cleaned_dataframe
                    .select_dtypes(
                        include=[
                            "object",
                            "category"
                        ]
                    )
                    .columns
                )

                for column in (
                    categorical_columns_cleaning
                ):

                    missing_count = int(
                        cleaned_dataframe[column]
                        .isnull()
                        .sum()
                    )

                    if missing_count > 0:

                        cleaned_dataframe[
                            column
                        ] = (
                            cleaned_dataframe[
                                column
                            ]
                            .fillna("Unknown")
                        )

                        categorical_values_filled += (
                            missing_count
                        )

                # -------------------------------------------------
                # Final cleaning statistics
                # -------------------------------------------------

                final_missing = int(
                    cleaned_dataframe
                    .isnull()
                    .sum()
                    .sum()
                )

                final_duplicates = int(
                    cleaned_dataframe
                    .duplicated()
                    .sum()
                )

                final_rows = len(
                    cleaned_dataframe
                )

                rows_removed = (
                    rows_before_cleaning
                    -
                    final_rows
                )

                # -------------------------------------------------
                # Save REAL cleaned version
                # -------------------------------------------------

                original_version = (
                    create_original_dataset_version(
                        dataset
                    )
                )

                cleaned_version = (
                    create_cleaned_dataset_version(
                        dataset,
                        cleaned_dataframe,
                        cleaned_missing,
                        final_missing,
                        cleaned_duplicates,
                        final_duplicates,
                    )
                )

                if cleaned_version is None:

                    raise ValueError(
                        "Smart BI could not create "
                        "the cleaned dataset version."
                    )

                # -------------------------------------------------
                # Cleaning activity
                # -------------------------------------------------

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Cleaned",

                    status="Success",

                    title=(
                        "Automatic data cleaning completed"
                    ),

                    description=(
                        "Smart BI automatically "
                        "handled duplicate rows, "
                        "empty rows and missing "
                        "values where possible."
                    ),

                    details={

                        "rows_before":
                            rows_before_cleaning,

                        "rows_after":
                            final_rows,

                        "rows_removed":
                            rows_removed,

                        "missing_before":
                            cleaned_missing,

                        "missing_after":
                            final_missing,

                        "duplicates_before":
                            cleaned_duplicates,

                        "duplicates_after":
                            final_duplicates,

                        "empty_rows_removed":
                            empty_rows_removed,

                        "duplicate_rows_removed":
                            duplicate_rows_removed,

                        "numeric_values_filled":
                            numeric_values_filled,

                        "categorical_values_filled":
                            categorical_values_filled,

                        "cleaned_version":
                            cleaned_version.version_number,

                        "quality_score":
                            cleaned_version.quality_score,
                    }
                )

                # =================================================
                # 11. ANALYTICS READY
                # =================================================

                DatasetActivity.objects.create(

                    dataset=dataset,

                    activity_type="Analytics Ready",

                    status="Success",

                    title=(
                        "Dataset is ready for analytics"
                    ),

                    description=(
                        "The dataset has completed "
                        "the automatic Smart BI "
                        "preparation pipeline and "
                        "a cleaned version is available."
                    ),

                    details={

                        "quality_score":
                            cleaned_version.quality_score,

                        "rows":
                            cleaned_version.total_rows,

                        "columns":
                            cleaned_version.total_columns,

                        "missing_values":
                            cleaned_version.missing_values,

                        "duplicate_rows":
                            cleaned_version.duplicate_rows,

                        "current_version":
                            cleaned_version.version_number,

                        "status":
                            "Analytics Ready",
                    }
                )

                # =================================================
                # 12. SUCCESS MESSAGE
                # =================================================

                messages.success(

                    request,

                    (
                        f"{dataset.name} uploaded and "
                        "automatically processed successfully."
                    )
                )

                return redirect(
                    "data_management:dataset_management"
                )

            except Exception as error:

                messages.error(

                    request,

                    (
                        "Unable to process dataset: "
                        f"{error}"
                    )
                )

        # Form invalid

    else:

        form = DatasetUploadForm()

    return render(

        request,

        "data_management/upload.html",

        {
            "form": form
        }
    )


# ============================================================
# DATASET PREVIEW
# ============================================================

@login_required
def dataset_preview(request, dataset_id):
    if not user_is_approved(request):
        return redirect("accounts:login")

    dataset = Dataset.objects.filter(
        id=dataset_id,
        owner=request.user,
        is_active=True
    ).first()

    if not dataset:
        messages.error(request, "Dataset not found.")
        return redirect("data_management:dataset_management")

    # ---------------------------------------------------------
    # Select requested version
    # ---------------------------------------------------------
    version_id = request.GET.get("version")
    selected_version = None

    if version_id:
        try:
            selected_version = DatasetVersion.objects.filter(
                id=version_id,
                dataset=dataset
            ).first()
        except (ValueError, TypeError):
            selected_version = None

    # Default = current cleaned version
    if selected_version is None:
        selected_version = DatasetVersion.objects.filter(
            dataset=dataset,
            version_type="Cleaned",
            is_current=True
        ).first()

    # Fallback = original
    if selected_version is None:
        selected_version = DatasetVersion.objects.filter(
            dataset=dataset,
            version_type="Original"
        ).first()

    # ---------------------------------------------------------
    # Select file
    # ---------------------------------------------------------
    file_to_read = None

    if selected_version and selected_version.file:
        file_to_read = selected_version.file
    elif dataset.file:
        file_to_read = dataset.file

    if not file_to_read:
        messages.error(request, "Dataset file could not be found.")
        return redirect("data_management:dataset_management")

    # ---------------------------------------------------------
    # Read dataframe
    # ---------------------------------------------------------
    dataframe = None

    try:
        filename = ""

        if selected_version:
            filename = selected_version.file_name or ""

        if not filename:
            filename = dataset.original_filename or dataset.file.name

        filename_lower = filename.lower()

        # Open the Django FileField directly
        file_to_read.open("rb")

        if filename_lower.endswith(".csv"):
            dataframe = pd.read_csv(file_to_read)

        elif filename_lower.endswith(".xlsx"):
            dataframe = pd.read_excel(
                file_to_read,
                engine="openpyxl"
            )

        elif filename_lower.endswith(".xls"):
            dataframe = pd.read_excel(file_to_read)

        else:
            messages.error(
                request,
                f"Unsupported file format: {filename}"
            )
            return redirect("data_management:dataset_management")

        file_to_read.close()

    except Exception as error:
        try:
            file_to_read.close()
        except Exception:
            pass

        messages.error(
            request,
            f"Unable to read dataset: {error}"
        )

        return redirect("data_management:dataset_management")

    # ---------------------------------------------------------
    # Prepare preview
    # ---------------------------------------------------------
    dataframe = dataframe.fillna("")

    preview_dataframe = dataframe.head(20)

    columns = [
        str(column)
        for column in preview_dataframe.columns
    ]

    rows = []

    for _, row in preview_dataframe.iterrows():
        rows.append([
            str(value)
            for value in row.tolist()
        ])

    # ---------------------------------------------------------
    # Version labels
    # ---------------------------------------------------------
    if selected_version:

        if selected_version.version_type == "Cleaned":
            version_label = "Current Cleaned Data"
            version_badge = "Analytics Ready"

        elif selected_version.version_type == "Original":
            version_label = "Original Uploaded Data"
            version_badge = "Original"

        else:
            version_label = (
                f"Version {selected_version.version_number}"
            )
            version_badge = selected_version.version_type

    else:
        version_label = "Uploaded Data"
        version_badge = "Original"

    # ---------------------------------------------------------
    # Original / cleaned versions
    # ---------------------------------------------------------
    original_version = DatasetVersion.objects.filter(
        dataset=dataset,
        version_type="Original"
    ).first()

    cleaned_version = DatasetVersion.objects.filter(
        dataset=dataset,
        version_type="Cleaned",
        is_current=True
    ).first()

    # ---------------------------------------------------------
    # Context
    # ---------------------------------------------------------
    context = {
        "dataset": dataset,

        "version": selected_version,
        "selected_version": selected_version,

        "version_label": version_label,
        "version_badge": version_badge,

        "columns": columns,
        "rows": rows,
        "preview_rows": len(rows),

        "total_rows": (
            selected_version.total_rows
            if selected_version
            else len(dataframe)
        ),

        "total_columns": (
            selected_version.total_columns
            if selected_version
            else len(dataframe.columns)
        ),

        "missing_values": (
            selected_version.missing_values
            if selected_version
            else int(dataframe.isna().sum().sum())
        ),

        "duplicate_rows": (
            selected_version.duplicate_rows
            if selected_version
            else int(dataframe.duplicated().sum())
        ),

        "quality_score": (
            selected_version.quality_score
            if selected_version
            else dataset.quality_score
        ),

        "is_original": (
            selected_version is not None
            and selected_version.version_type == "Original"
        ),

        "is_cleaned": (
            selected_version is not None
            and selected_version.version_type == "Cleaned"
        ),

        "original_version": original_version,
        "cleaned_version": cleaned_version,
    }

    return render(
        request,
        "data_management/dataset_preview.html",
        context
    )

# ============================================================
# DATASET MANAGEMENT
# ============================================================

@login_required
def dataset_management(request):

    if not user_is_approved(request):
        return redirect("accounts:login")

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True
        )
        .prefetch_related(
            Prefetch(
                "activities",
                queryset=DatasetActivity.objects.order_by(
                    "created_at"
                )
            ),
            Prefetch(
                "versions",
                queryset=DatasetVersion.objects.order_by(
                    "-version_number"
                )
            )
        )
        .order_by("-uploaded_at")
    )

    for dataset in datasets:

        versions = list(dataset.versions.all())

        # -----------------------------------------
        # ORIGINAL VERSION
        # -----------------------------------------

        original_version = next(
            (
                version
                for version in versions
                if version.version_type == "Original"
            ),
            None
        )

        # -----------------------------------------
        # CURRENT CLEANED VERSION
        # -----------------------------------------

        cleaned_version = next(
            (
                version
                for version in versions
                if (
                    version.version_type == "Cleaned"
                    and version.is_current
                )
            ),
            None
        )

        # Fallback: latest cleaned version
        if cleaned_version is None:

            cleaned_versions = [
                version
                for version in versions
                if version.version_type == "Cleaned"
            ]

            if cleaned_versions:
                cleaned_version = max(
                    cleaned_versions,
                    key=lambda version: version.version_number
                )

        # -----------------------------------------
        # ATTACH DATA FOR TEMPLATE
        # -----------------------------------------

        dataset.original_version = original_version
        dataset.cleaned_version = cleaned_version

        # -----------------------------------------
        # CURRENT STATUS
        # -----------------------------------------

        if cleaned_version:
            dataset.processing_status = "Analytics Ready"
        else:
            dataset.processing_status = "Processing"

    return render(
        request,
        "data_management/dataset_list.html",
        {
            "datasets": datasets,
        }
    )


# ============================================================
# DATA QUALITY
# ============================================================

@login_required
def data_quality(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    quality_data = None

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

    if selected_dataset:

        try:

            dataframe = read_dataset_file(
                selected_dataset
            )

            total_rows = len(
                dataframe
            )

            total_columns = len(
                dataframe.columns
            )

            missing_values = int(
                dataframe
                .isnull()
                .sum()
                .sum()
            )

            duplicate_rows = int(
                dataframe
                .duplicated()
                .sum()
            )

            if total_rows > 0:

                incomplete_rows = int(
                    dataframe
                    .isnull()
                    .any(axis=1)
                    .sum()
                )

                complete_rows = (
                    total_rows
                    -
                    incomplete_rows
                )

                missing_percentage = round(
                    (
                        missing_values
                        /
                        (
                            total_rows
                            *
                            total_columns
                        )
                    )
                    * 100,
                    2
                ) if total_columns else 0

                duplicate_percentage = round(
                    (
                        duplicate_rows
                        /
                        total_rows
                    )
                    * 100,
                    2
                )

            else:

                complete_rows = 0
                incomplete_rows = 0
                missing_percentage = 0
                duplicate_percentage = 0

            quality_score = (
                calculate_quality_score(
                    dataframe,
                    missing_values,
                    duplicate_rows
                )
            )

            if quality_score >= 90:

                quality_status = "Excellent"
                quality_class = "excellent"

            elif quality_score >= 75:

                quality_status = "Good"
                quality_class = "good"

            elif quality_score >= 50:

                quality_status = "Needs Attention"
                quality_class = "attention"

            else:

                quality_status = "Critical"
                quality_class = "critical"

            column_quality = []

            for column in dataframe.columns:

                column_missing = int(
                    dataframe[column]
                    .isnull()
                    .sum()
                )

                column_missing_percentage = round(
                    (
                        column_missing
                        /
                        total_rows
                    )
                    * 100,
                    2
                ) if total_rows else 0

                column_duplicates = int(
                    dataframe[column]
                    .duplicated()
                    .sum()
                )

                non_null_values = int(
                    dataframe[column]
                    .notnull()
                    .sum()
                )

                if column_missing_percentage == 0:

                    column_status = "Excellent"
                    column_class = "excellent"

                elif column_missing_percentage <= 5:

                    column_status = "Good"
                    column_class = "good"

                elif column_missing_percentage <= 20:

                    column_status = "Attention"
                    column_class = "attention"

                else:

                    column_status = "Critical"
                    column_class = "critical"

                column_quality.append(
                    {
                        "name":
                            str(column),

                        "data_type":
                            str(
                                dataframe[
                                    column
                                ].dtype
                            ),

                        "missing":
                            column_missing,

                        "missing_percentage":
                            column_missing_percentage,

                        "non_null":
                            non_null_values,

                        "duplicates":
                            column_duplicates,

                        "status":
                            column_status,

                        "status_class":
                            column_class,
                    }
                )

            quality_data = {

                "total_rows":
                    total_rows,

                "total_columns":
                    total_columns,

                "missing_values":
                    missing_values,

                "duplicate_rows":
                    duplicate_rows,

                "complete_rows":
                    complete_rows,

                "incomplete_rows":
                    incomplete_rows,

                "missing_percentage":
                    missing_percentage,

                "duplicate_percentage":
                    duplicate_percentage,

                "quality_score":
                    quality_score,

                "quality_status":
                    quality_status,

                "quality_class":
                    quality_class,

                "column_quality":
                    column_quality,
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to analyze dataset: "
                    f"{error}"
                )
            )

    return render(
        request,
        "data_management/data_quality.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "quality":
                quality_data,
        }
    )


# ============================================================
# DATA CLEANING
# ============================================================

@login_required
def data_cleaning(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    cleaning_data = None

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

    if selected_dataset:

        try:

            dataframe = read_dataset_file(
                selected_dataset
            )

            before_rows = len(
                dataframe
            )

            before_columns = len(
                dataframe.columns
            )

            before_missing = int(
                dataframe
                .isnull()
                .sum()
                .sum()
            )

            before_duplicates = int(
                dataframe
                .duplicated()
                .sum()
            )

            empty_rows = int(
                dataframe
                .isnull()
                .all(axis=1)
                .sum()
            )

            dataframe = (
                dataframe
                .dropna(how="all")
            )

            text_columns_cleaned = 0

            for column in dataframe.columns:

                if (
                    dataframe[column]
                    .dtype
                    == "object"
                ):

                    original_values = (
                        dataframe[column]
                        .copy()
                    )

                    dataframe[column] = (
                        dataframe[column]
                        .apply(
                            lambda value:
                            value.strip()
                            if isinstance(
                                value,
                                str
                            )
                            else value
                        )
                    )

                    changed_values = (
                        original_values
                        !=
                        dataframe[column]
                    ).sum()

                    if changed_values > 0:

                        text_columns_cleaned += 1

            duplicates_removed = int(
                dataframe
                .duplicated()
                .sum()
            )

            dataframe = (
                dataframe
                .drop_duplicates()
            )

            after_missing = int(
                dataframe
                .isnull()
                .sum()
                .sum()
            )

            after_rows = len(
                dataframe
            )

            after_columns = len(
                dataframe.columns
            )

            after_duplicates = int(
                dataframe
                .duplicated()
                .sum()
            )

            rows_removed = (
                before_rows
                -
                after_rows
            )

            missing_reduction = (
                before_missing
                -
                after_missing
            )

            total_cleaning_actions = (
                empty_rows
                +
                duplicates_removed
                +
                text_columns_cleaned
            )

            cleaning_data = {

                "before_rows":
                    before_rows,

                "before_columns":
                    before_columns,

                "before_missing":
                    before_missing,

                "before_duplicates":
                    before_duplicates,

                "after_rows":
                    after_rows,

                "after_columns":
                    after_columns,

                "after_missing":
                    after_missing,

                "after_duplicates":
                    after_duplicates,

                "empty_rows":
                    empty_rows,

                "duplicates_removed":
                    duplicates_removed,

                "rows_removed":
                    rows_removed,

                "missing_reduction":
                    missing_reduction,

                "text_columns_cleaned":
                    text_columns_cleaned,

                "total_actions":
                    total_cleaning_actions,
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to clean dataset: "
                    f"{error}"
                )
            )

    return render(
        request,
        "data_management/data_cleaning.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "cleaning":
                cleaning_data,
        }
    )


# ============================================================
# DOWNLOAD CLEANED DATASET
# ============================================================

@login_required
def download_cleaned_dataset(
    request,
    dataset_id
):

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

    dataset = (
        Dataset.objects
        .filter(
            id=dataset_id,
            owner=request.user,
            is_active=True
        )
        .first()
    )

    if dataset is None:

        messages.error(
            request,
            "Dataset not found."
        )

        return redirect(
            "data_management:data_cleaning"
        )

    # --------------------------------------------------------
    # Find latest cleaned version
    # --------------------------------------------------------

    cleaned_version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            version_type="Cleaned"
        )
        .order_by(
            "-version_number"
        )
        .first()
    )

    if cleaned_version is None:

        messages.warning(
            request,
            "No cleaned version is available yet."
        )

        return redirect(
            "data_management:data_cleaning"
        )

    try:

        file_handle = (
            cleaned_version
            .file
            .open("rb")
        )

        response = HttpResponse(
            file_handle,
            content_type="text/csv"
        )

        safe_name = (
            dataset.name
            .replace(" ", "_")
            .replace("/", "_")
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{safe_name}_'
            f'cleaned_v'
            f'{cleaned_version.version_number}'
            f'.csv"'
        )

        return response

    except Exception as error:

        messages.error(
            request,
            (
                "Unable to download cleaned "
                f"dataset: {error}"
            )
        )

        return redirect(
            "data_management:data_cleaning"
        )


# ============================================================
# DATA VALIDATION
# ============================================================

@login_required
def data_validation(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    validation = None

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

    if selected_dataset:

        try:

            dataframe = read_dataset_file(
                selected_dataset
            )

            # ------------------------------------------------
            # NORMALIZE COLUMN NAMES
            # ------------------------------------------------

            dataframe.columns = [
                str(column).strip()
                for column
                in dataframe.columns
            ]

            columns = list(
                dataframe.columns
            )

            lower_columns = {
                str(column).lower():
                column
                for column
                in columns
            }

            total_rows = len(
                dataframe
            )

            # ------------------------------------------------
            # REQUIRED COLUMNS
            # ------------------------------------------------

            dataset_type = (
                selected_dataset.dataset_type
            )

            required_columns = []

            if dataset_type == "Sales":

                required_columns = [
                    "date",
                    "sales",
                ]

            elif dataset_type == "Customers":

                required_columns = [
                    "customer",
                ]

            elif dataset_type == "Products":

                required_columns = [
                    "product",
                ]

            elif dataset_type == "Regional":

                required_columns = [
                    "region",
                    "sales",
                ]

            elif dataset_type == "Marketing":

                required_columns = [
                    "date",
                ]

            elif dataset_type == "Financial":

                required_columns = [
                    "date",
                ]

            elif dataset_type == "Returns":

                required_columns = [
                    "date",
                ]

            missing_required_columns = []

            for required_column in (
                required_columns
            ):

                if (
                    required_column
                    not in lower_columns
                ):

                    missing_required_columns.append(
                        required_column.title()
                    )

            # ------------------------------------------------
            # COLUMN FINDER
            # ------------------------------------------------

            def find_column(
                possible_names
            ):

                for name in possible_names:

                    if (
                        name.lower()
                        in lower_columns
                    ):

                        return (
                            lower_columns[
                                name.lower()
                            ]
                        )

                return None

            date_column = find_column(
                [
                    "date",
                    "order_date",
                    "transaction_date",
                    "sale_date",
                ]
            )

            sales_column = find_column(
                [
                    "sales",
                    "revenue",
                    "amount",
                    "total_sales",
                ]
            )

            quantity_column = find_column(
                [
                    "quantity",
                    "qty",
                    "units",
                ]
            )

            discount_column = find_column(
                [
                    "discount",
                    "discount_percent",
                    "discount_percentage",
                ]
            )

            # ------------------------------------------------
            # VALIDATION
            # ------------------------------------------------

            validation_errors = []

            row_failed_flags = []

            duplicate_mask = (
                dataframe
                .duplicated(
                    keep=False
                )
            )

            empty_rows = int(
                dataframe
                .isnull()
                .all(axis=1)
                .sum()
            )

            for position, (
                index,
                row
            ) in enumerate(
                dataframe.iterrows()
            ):

                row_errors = []

                # --------------------------------------------
                # Empty row
                # --------------------------------------------

                if row.isnull().all():

                    row_errors.append(
                        "Empty row"
                    )

                # --------------------------------------------
                # Missing values
                # --------------------------------------------

                missing_fields = []

                for column in columns:

                    if pd.isna(
                        row[column]
                    ):

                        missing_fields.append(
                            str(column)
                        )

                if missing_fields:

                    row_errors.append(
                        "Missing value in: "
                        +
                        ", ".join(
                            missing_fields[:5]
                        )
                    )

                # --------------------------------------------
                # Date validation
                # --------------------------------------------

                if date_column:

                    date_value = row[
                        date_column
                    ]

                    if not pd.isna(
                        date_value
                    ):

                        converted_date = (
                            pd.to_datetime(
                                date_value,
                                errors="coerce"
                            )
                        )

                        if pd.isna(
                            converted_date
                        ):

                            row_errors.append(
                                "Invalid date"
                            )

                # --------------------------------------------
                # Sales validation
                # --------------------------------------------

                if sales_column:

                    sales_value = row[
                        sales_column
                    ]

                    if not pd.isna(
                        sales_value
                    ):

                        numeric_sales = (
                            pd.to_numeric(
                                sales_value,
                                errors="coerce"
                            )
                        )

                        if pd.isna(
                            numeric_sales
                        ):

                            row_errors.append(
                                "Sales must be numeric"
                            )

                        elif numeric_sales < 0:

                            row_errors.append(
                                "Sales cannot be negative"
                            )

                # --------------------------------------------
                # Quantity validation
                # --------------------------------------------

                if quantity_column:

                    quantity_value = row[
                        quantity_column
                    ]

                    if not pd.isna(
                        quantity_value
                    ):

                        numeric_quantity = (
                            pd.to_numeric(
                                quantity_value,
                                errors="coerce"
                            )
                        )

                        if pd.isna(
                            numeric_quantity
                        ):

                            row_errors.append(
                                "Quantity must be numeric"
                            )

                        elif numeric_quantity < 0:

                            row_errors.append(
                                "Quantity cannot be negative"
                            )

                # --------------------------------------------
                # Discount validation
                # --------------------------------------------

                if discount_column:

                    discount_value = row[
                        discount_column
                    ]

                    if not pd.isna(
                        discount_value
                    ):

                        numeric_discount = (
                            pd.to_numeric(
                                discount_value,
                                errors="coerce"
                            )
                        )

                        if pd.isna(
                            numeric_discount
                        ):

                            row_errors.append(
                                "Discount must be numeric"
                            )

                        elif (
                            numeric_discount < 0
                            or
                            numeric_discount > 100
                        ):

                            row_errors.append(
                                "Discount must be between 0 and 100"
                            )

                # --------------------------------------------
                # Duplicate validation
                # --------------------------------------------

                if bool(
                    duplicate_mask.iloc[
                        position
                    ]
                ):

                    row_errors.append(
                        "Duplicate row"
                    )

                has_error = bool(
                    row_errors
                )

                row_failed_flags.append(
                    has_error
                )

                if has_error:

                    validation_errors.append(
                        {
                            "row_number":
                                position + 2,

                            "reason":
                                "; ".join(
                                    row_errors
                                ),
                        }
                    )

            # ------------------------------------------------
            # Correct row counts
            # ------------------------------------------------

            failed_rows = sum(
                row_failed_flags
            )

            passed_rows = (
                total_rows
                -
                failed_rows
            )

            # ------------------------------------------------
            # Required column issue
            # ------------------------------------------------

            if missing_required_columns:

                validation_errors.insert(
                    0,
                    {
                        "row_number":
                            "-",

                        "reason":
                            (
                                "Missing required "
                                "column(s): "
                                +
                                ", ".join(
                                    missing_required_columns
                                )
                            ),
                    }
                )

            # ------------------------------------------------
            # Score
            # ------------------------------------------------

            if total_rows > 0:

                validation_score = round(
                    (
                        passed_rows
                        /
                        total_rows
                    )
                    * 100,
                    2
                )

            else:

                validation_score = 0

            if missing_required_columns:

                validation_score = 0

            validation_score = max(
                0,
                min(
                    100,
                    validation_score
                )
            )

            # ------------------------------------------------
            # Status
            # ------------------------------------------------

            if validation_score >= 95:

                validation_status = "Excellent"
                validation_class = "excellent"

            elif validation_score >= 80:

                validation_status = "Good"
                validation_class = "good"

            elif validation_score >= 60:

                validation_status = "Needs Attention"
                validation_class = "attention"

            else:

                validation_status = "Critical"
                validation_class = "critical"

            # ------------------------------------------------
            # Validation rule count
            # ------------------------------------------------

            validation_rules = 0

            if missing_required_columns:

                validation_rules += 1

            validation_rules += 1
            validation_rules += 1

            if date_column:
                validation_rules += 1

            if sales_column:
                validation_rules += 1

            if quantity_column:
                validation_rules += 1

            if discount_column:
                validation_rules += 1

            validation = {

                "dataset_type":
                    dataset_type,

                "total_rows":
                    total_rows,

                "passed_rows":
                    passed_rows,

                "failed_rows":
                    failed_rows,

                "validation_score":
                    validation_score,

                "validation_status":
                    validation_status,

                "validation_class":
                    validation_class,

                "duplicate_rows":
                    int(
                        duplicate_mask.sum()
                    ),

                "empty_rows":
                    empty_rows,

                "missing_required_columns":
                    missing_required_columns,

                "validation_errors":
                    validation_errors[:200],

                "validation_rules":
                    validation_rules,

                "date_column":
                    date_column,

                "sales_column":
                    sales_column,

                "quantity_column":
                    quantity_column,

                "discount_column":
                    discount_column,

                "total_errors":
                    len(validation_errors),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to validate dataset: "
                    f"{error}"
                )
            )

    return render(
        request,
        "data_management/data_validation.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "validation":
                validation,
        }
    )


# ============================================================
# DOWNLOAD VALIDATION REPORT
# ============================================================

@login_required
def download_validation_report(
    request,
    dataset_id
):

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

    dataset = (
        Dataset.objects
        .filter(
            id=dataset_id,
            owner=request.user,
            is_active=True
        )
        .first()
    )

    if dataset is None:

        messages.error(
            request,
            "Dataset not found."
        )

        return redirect(
            "data_management:data_validation"
        )

    try:

        dataframe = read_dataset_file(
            dataset
        )

        dataframe.columns = [
            str(column).strip()
            for column
            in dataframe.columns
        ]

        columns = list(
            dataframe.columns
        )

        lower_columns = {
            str(column).lower():
            column
            for column
            in columns
        }

        def find_column(
            possible_names
        ):

            for name in possible_names:

                if (
                    name.lower()
                    in lower_columns
                ):

                    return (
                        lower_columns[
                            name.lower()
                        ]
                    )

            return None

        date_column = find_column(
            [
                "date",
                "order_date",
                "transaction_date",
                "sale_date",
            ]
        )

        sales_column = find_column(
            [
                "sales",
                "revenue",
                "amount",
                "total_sales",
            ]
        )

        quantity_column = find_column(
            [
                "quantity",
                "qty",
                "units",
            ]
        )

        discount_column = find_column(
            [
                "discount",
                "discount_percent",
                "discount_percentage",
            ]
        )

        duplicate_mask = (
            dataframe
            .duplicated(
                keep=False
            )
        )

        report_rows = []

        for position, (
            index,
            row
        ) in enumerate(
            dataframe.iterrows()
        ):

            errors = []

            # ------------------------------------------------
            # Missing values
            # ------------------------------------------------

            missing_fields = []

            for column in columns:

                if pd.isna(
                    row[column]
                ):

                    missing_fields.append(
                        str(column)
                    )

            if missing_fields:

                errors.append(
                    "Missing value in: "
                    +
                    ", ".join(
                        missing_fields[:5]
                    )
                )

            # ------------------------------------------------
            # Date
            # ------------------------------------------------

            if date_column:

                value = row[
                    date_column
                ]

                if not pd.isna(value):

                    parsed_date = (
                        pd.to_datetime(
                            value,
                            errors="coerce"
                        )
                    )

                    if pd.isna(
                        parsed_date
                    ):

                        errors.append(
                            "Invalid date"
                        )

            # ------------------------------------------------
            # Sales
            # ------------------------------------------------

            if sales_column:

                value = row[
                    sales_column
                ]

                if not pd.isna(value):

                    numeric_value = (
                        pd.to_numeric(
                            value,
                            errors="coerce"
                        )
                    )

                    if pd.isna(
                        numeric_value
                    ):

                        errors.append(
                            "Sales must be numeric"
                        )

                    elif numeric_value < 0:

                        errors.append(
                            "Sales cannot be negative"
                        )

            # ------------------------------------------------
            # Quantity
            # ------------------------------------------------

            if quantity_column:

                value = row[
                    quantity_column
                ]

                if not pd.isna(value):

                    numeric_value = (
                        pd.to_numeric(
                            value,
                            errors="coerce"
                        )
                    )

                    if pd.isna(
                        numeric_value
                    ):

                        errors.append(
                            "Quantity must be numeric"
                        )

                    elif numeric_value < 0:

                        errors.append(
                            "Quantity cannot be negative"
                        )

            # ------------------------------------------------
            # Discount
            # ------------------------------------------------

            if discount_column:

                value = row[
                    discount_column
                ]

                if not pd.isna(value):

                    numeric_value = (
                        pd.to_numeric(
                            value,
                            errors="coerce"
                        )
                    )

                    if pd.isna(
                        numeric_value
                    ):

                        errors.append(
                            "Discount must be numeric"
                        )

                    elif (
                        numeric_value < 0
                        or
                        numeric_value > 100
                    ):

                        errors.append(
                            "Discount must be between 0 and 100"
                        )

            # ------------------------------------------------
            # Duplicate
            # ------------------------------------------------

            is_duplicate = bool(
                duplicate_mask.iloc[
                    position
                ]
            )

            if is_duplicate:

                errors.append(
                    "Duplicate row"
                )

            report_rows.append(
                {
                    "row_number":
                        position + 2,

                    "status":
                        (
                            "FAILED"
                            if errors
                            else "PASSED"
                        ),

                    "reason":
                        (
                            "; ".join(errors)
                            if errors
                            else "Valid record"
                        ),
                }
            )

        report_dataframe = pd.DataFrame(
            report_rows
        )

        response = HttpResponse(
            content_type="text/csv"
        )

        safe_name = (
            dataset.name
            .replace(" ", "_")
            .replace("/", "_")
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="validation_report_'
            f'{safe_name}.csv"'
        )

        report_dataframe.to_csv(
            response,
            index=False
        )

        return response

    except Exception as error:

        messages.error(
            request,
            (
                "Unable to generate validation "
                f"report: {error}"
            )
        )

        return redirect(
            "data_management:data_validation"
        )


# ============================================================
# DATA PROFILING
# ============================================================

@login_required
def data_profiling(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    profiling = None

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

    if selected_dataset:

        try:

            dataframe = read_dataset_file(
                selected_dataset
            )

            # ------------------------------------------------
            # BASIC INFORMATION
            # ------------------------------------------------

            total_rows = len(
                dataframe
            )

            total_columns = len(
                dataframe.columns
            )

            total_cells = (
                total_rows
                *
                total_columns
            )

            missing_values = int(
                dataframe
                .isnull()
                .sum()
                .sum()
            )

            duplicate_rows = int(
                dataframe
                .duplicated()
                .sum()
            )

            complete_cells = (
                total_cells
                -
                missing_values
            )

            completeness = (
                (
                    complete_cells
                    /
                    total_cells
                )
                * 100
                if total_cells
                else 0
            )

            completeness = round(
                completeness,
                2
            )

            numeric_columns = list(
                dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            )

            categorical_columns = list(
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category",
                        "bool"
                    ]
                )
                .columns
            )

            datetime_columns = list(
                dataframe
                .select_dtypes(
                    include=[
                        "datetime"
                    ]
                )
                .columns
            )

            # ------------------------------------------------
            # COLUMN PROFILES
            # ------------------------------------------------

            column_profiles = []

            for column in dataframe.columns:

                series = dataframe[
                    column
                ]

                data_type = str(
                    series.dtype
                )

                missing = int(
                    series.isnull().sum()
                )

                non_null = int(
                    series.notnull().sum()
                )

                unique_values = int(
                    series.nunique(
                        dropna=True
                    )
                )

                duplicate_values = max(
                    0,
                    non_null
                    -
                    unique_values
                )

                missing_percentage = (
                    (
                        missing
                        /
                        total_rows
                    )
                    * 100
                    if total_rows
                    else 0
                )

                missing_percentage = round(
                    missing_percentage,
                    2
                )

                minimum = "-"
                maximum = "-"
                mean = "-"
                median = "-"
                standard_deviation = "-"

                if pd.api.types.is_numeric_dtype(
                    series
                ):

                    if series.notna().any():

                        minimum = round(
                            float(
                                series.min()
                            ),
                            2
                        )

                        maximum = round(
                            float(
                                series.max()
                            ),
                            2
                        )

                        mean = round(
                            float(
                                series.mean()
                            ),
                            2
                        )

                        median = round(
                            float(
                                series.median()
                            ),
                            2
                        )

                        standard_deviation = round(
                            float(
                                series.std()
                            )
                            if series.notna().sum() > 1
                            else 0,
                            2
                        )

                top_value = "-"
                top_frequency = 0

                if (
                    series.dtype == "object"
                    or
                    str(series.dtype)
                    == "category"
                    or
                    str(series.dtype)
                    == "bool"
                ):

                    value_counts = (
                        series
                        .dropna()
                        .value_counts()
                    )

                    if not value_counts.empty:

                        top_value = str(
                            value_counts.index[0]
                        )

                        top_frequency = int(
                            value_counts.iloc[0]
                        )

                if pd.api.types.is_numeric_dtype(
                    series
                ):

                    column_type = "Numeric"
                    type_class = "numeric"

                elif (
                    pd.api.types.is_datetime64_any_dtype(
                        series
                    )
                ):

                    column_type = "Date / Time"
                    type_class = "datetime"

                else:

                    column_type = "Categorical"
                    type_class = "categorical"

                if missing_percentage == 0:

                    health = "Healthy"
                    health_class = "healthy"

                elif missing_percentage <= 5:

                    health = "Good"
                    health_class = "good"

                elif missing_percentage <= 20:

                    health = "Attention"
                    health_class = "attention"

                else:

                    health = "Critical"
                    health_class = "critical"

                column_profiles.append(
                    {
                        "name":
                            str(column),

                        "data_type":
                            data_type,

                        "column_type":
                            column_type,

                        "type_class":
                            type_class,

                        "non_null":
                            non_null,

                        "missing":
                            missing,

                        "missing_percentage":
                            missing_percentage,

                        "unique":
                            unique_values,

                        "duplicates":
                            duplicate_values,

                        "minimum":
                            minimum,

                        "maximum":
                            maximum,

                        "mean":
                            mean,

                        "median":
                            median,

                        "standard_deviation":
                            standard_deviation,

                        "top_value":
                            top_value,

                        "top_frequency":
                            top_frequency,

                        "health":
                            health,

                        "health_class":
                            health_class,
                    }
                )

            # ------------------------------------------------
            # NUMERIC SUMMARY
            # ------------------------------------------------

            numeric_summary = []

            for column in numeric_columns:

                series = dataframe[
                    column
                ]

                valid_series = (
                    series.dropna()
                )

                if valid_series.empty:

                    continue

                numeric_summary.append(
                    {
                        "name":
                            str(column),

                        "minimum":
                            round(
                                float(
                                    valid_series.min()
                                ),
                                2
                            ),

                        "maximum":
                            round(
                                float(
                                    valid_series.max()
                                ),
                                2
                            ),

                        "mean":
                            round(
                                float(
                                    valid_series.mean()
                                ),
                                2
                            ),

                        "median":
                            round(
                                float(
                                    valid_series.median()
                                ),
                                2
                            ),

                        "std":
                            round(
                                float(
                                    valid_series.std()
                                )
                                if len(
                                    valid_series
                                ) > 1
                                else 0,
                                2
                            ),
                    }
                )

            # ------------------------------------------------
            # CATEGORICAL SUMMARY
            # ------------------------------------------------

            categorical_summary = []

            for column in categorical_columns:

                value_counts = (
                    dataframe[column]
                    .dropna()
                    .value_counts()
                    .head(5)
                )

                values = []

                for value, count in (
                    value_counts.items()
                ):

                    values.append(
                        {
                            "value":
                                str(value),

                            "count":
                                int(count),
                        }
                    )

                categorical_summary.append(
                    {
                        "name":
                            str(column),

                        "values":
                            values,
                    }
                )

            # ------------------------------------------------
            # DATASET HEALTH
            # ------------------------------------------------

            if completeness >= 95:

                health_status = "Excellent"
                health_class = "excellent"

            elif completeness >= 85:

                health_status = "Good"
                health_class = "good"

            elif completeness >= 70:

                health_status = "Needs Attention"
                health_class = "attention"

            else:

                health_status = "Critical"
                health_class = "critical"

            profiling = {

                "total_rows":
                    total_rows,

                "total_columns":
                    total_columns,

                "total_cells":
                    total_cells,

                "missing_values":
                    missing_values,

                "duplicate_rows":
                    duplicate_rows,

                "completeness":
                    completeness,

                "numeric_count":
                    len(
                        numeric_columns
                    ),

                "categorical_count":
                    len(
                        categorical_columns
                    ),

                "datetime_count":
                    len(
                        datetime_columns
                    ),

                "column_profiles":
                    column_profiles,

                "numeric_summary":
                    numeric_summary,

                "categorical_summary":
                    categorical_summary,

                "health_status":
                    health_status,

                "health_class":
                    health_class,
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to profile dataset: "
                    f"{error}"
                )
            )

    return render(
        request,
        "data_management/data_profiling.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "profiling":
                profiling,
        }
    )


# ============================================================
# DATA TRANSFORMATION
# ============================================================

@login_required
def data_transformation(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    transformation = None

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

    if selected_dataset:

        try:

            dataframe = read_dataset_file(
                selected_dataset
            )

            dataframe.columns = [
                str(column).strip()
                for column
                in dataframe.columns
            ]

            numeric_columns = [
                str(column)
                for column
                in dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            ]

            categorical_columns = [
                str(column)
                for column
                in dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category",
                        "bool"
                    ]
                )
                .columns
            ]

            date_columns = []

            for column in dataframe.columns:

                column_name = (
                    str(column).lower()
                )

                if (
                    "date" in column_name
                    or
                    "time" in column_name
                ):

                    date_columns.append(
                        str(column)
                    )

            transformation = {

                "total_rows":
                    len(dataframe),

                "total_columns":
                    len(dataframe.columns),

                "numeric_columns":
                    numeric_columns,

                "categorical_columns":
                    categorical_columns,

                "date_columns":
                    date_columns,

                "columns": [

                    {
                        "name":
                            str(column),

                        "dtype":
                            str(
                                dataframe[
                                    column
                                ].dtype
                            ),

                        "missing":
                            int(
                                dataframe[
                                    column
                                ]
                                .isnull()
                                .sum()
                            ),

                        "unique":
                            int(
                                dataframe[
                                    column
                                ]
                                .nunique(
                                    dropna=True
                                )
                            ),
                    }

                    for column
                    in dataframe.columns
                ],

                "preview":
                    (
                        dataframe
                        .head(10)
                        .fillna("")
                        .to_dict(
                            orient="records"
                        )
                    ),

                "preview_columns":
                    [
                        str(column)
                        for column
                        in dataframe.columns
                    ],
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to load dataset: "
                    f"{error}"
                )
            )

    return render(
        request,
        "data_management/data_transformation.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "transformation":
                transformation,
        }
    )


# ============================================================
# TRANSFORM AND DOWNLOAD DATASET
# ============================================================

@login_required
def transform_dataset(
    request,
    dataset_id
):

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

    dataset = (
        Dataset.objects
        .filter(
            id=dataset_id,
            owner=request.user,
            is_active=True
        )
        .first()
    )

    if dataset is None:

        messages.error(
            request,
            "Dataset not found."
        )

        return redirect(
            "data_management:data_transformation"
        )

    try:

        dataframe = read_dataset_file(
            dataset
        )

        # ----------------------------------------------------
        # GET SETTINGS
        # ----------------------------------------------------

        trim_text = (
            request.POST.get(
                "trim_text"
            )
            == "on"
        )

        lowercase_text = (
            request.POST.get(
                "lowercase_text"
            )
            == "on"
        )

        uppercase_text = (
            request.POST.get(
                "uppercase_text"
            )
            == "on"
        )

        fill_numeric = (
            request.POST.get(
                "fill_numeric"
            )
            == "on"
        )

        fill_categorical = (
            request.POST.get(
                "fill_categorical"
            )
            == "on"
        )

        normalize = (
            request.POST.get(
                "normalize"
            )
            == "on"
        )

        standardize = (
            request.POST.get(
                "standardize"
            )
            == "on"
        )

        convert_dates = (
            request.POST.get(
                "convert_dates"
            )
            == "on"
        )

        actions = []

        # ----------------------------------------------------
        # TRIM TEXT
        # ----------------------------------------------------

        if trim_text:

            for column in dataframe.columns:

                if (
                    dataframe[column]
                    .dtype
                    == "object"
                ):

                    dataframe[column] = (
                        dataframe[column]
                        .apply(
                            lambda value:
                            value.strip()
                            if isinstance(
                                value,
                                str
                            )
                            else value
                        )
                    )

            actions.append(
                "Removed leading and trailing spaces"
            )

        # ----------------------------------------------------
        # LOWERCASE
        # ----------------------------------------------------

        if lowercase_text:

            for column in dataframe.columns:

                if (
                    dataframe[column]
                    .dtype
                    == "object"
                ):

                    dataframe[column] = (
                        dataframe[column]
                        .apply(
                            lambda value:
                            value.lower()
                            if isinstance(
                                value,
                                str
                            )
                            else value
                        )
                    )

            actions.append(
                "Converted text to lowercase"
            )

        # ----------------------------------------------------
        # UPPERCASE
        # ----------------------------------------------------

        if uppercase_text:

            for column in dataframe.columns:

                if (
                    dataframe[column]
                    .dtype
                    == "object"
                ):

                    dataframe[column] = (
                        dataframe[column]
                        .apply(
                            lambda value:
                            value.upper()
                            if isinstance(
                                value,
                                str
                            )
                            else value
                        )
                    )

            actions.append(
                "Converted text to uppercase"
            )

        # ----------------------------------------------------
        # NUMERIC MISSING VALUES
        # ----------------------------------------------------

        if fill_numeric:

            numeric_columns = (
                dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            )

            for column in numeric_columns:

                if dataframe[
                    column
                ].isnull().any():

                    median_value = (
                        dataframe[
                            column
                        ].median()
                    )

                    if pd.notna(
                        median_value
                    ):

                        dataframe[
                            column
                        ] = (
                            dataframe[
                                column
                            ]
                            .fillna(
                                median_value
                            )
                        )

            actions.append(
                "Filled numeric missing values using median"
            )

        # ----------------------------------------------------
        # CATEGORICAL MISSING VALUES
        # ----------------------------------------------------

        if fill_categorical:

            categorical_columns = (
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category",
                        "bool"
                    ]
                )
                .columns
            )

            for column in categorical_columns:

                if dataframe[
                    column
                ].isnull().any():

                    mode_values = (
                        dataframe[
                            column
                        ].mode()
                    )

                    if not mode_values.empty:

                        dataframe[
                            column
                        ] = (
                            dataframe[
                                column
                            ]
                            .fillna(
                                mode_values.iloc[0]
                            )
                        )

            actions.append(
                "Filled categorical missing values using mode"
            )

        # ----------------------------------------------------
        # NORMALIZATION
        # ----------------------------------------------------

        if normalize:

            numeric_columns = (
                dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            )

            for column in numeric_columns:

                minimum = dataframe[
                    column
                ].min()

                maximum = dataframe[
                    column
                ].max()

                if (
                    pd.notna(minimum)
                    and
                    pd.notna(maximum)
                    and
                    maximum != minimum
                ):

                    dataframe[column] = (
                        (
                            dataframe[column]
                            - minimum
                        )
                        /
                        (
                            maximum
                            - minimum
                        )
                    )

            actions.append(
                "Normalized numeric columns using Min-Max scaling"
            )

        # ----------------------------------------------------
        # STANDARDIZATION
        # ----------------------------------------------------

        if standardize:

            numeric_columns = (
                dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            )

            for column in numeric_columns:

                mean_value = (
                    dataframe[column]
                    .mean()
                )

                std_value = (
                    dataframe[column]
                    .std()
                )

                if (
                    pd.notna(std_value)
                    and
                    std_value != 0
                ):

                    dataframe[column] = (
                        (
                            dataframe[column]
                            - mean_value
                        )
                        /
                        std_value
                    )

            actions.append(
                "Standardized numeric columns using Z-score"
            )

        # ----------------------------------------------------
        # DATE CONVERSION
        # ----------------------------------------------------

        if convert_dates:

            for column in dataframe.columns:

                column_name = (
                    str(column).lower()
                )

                if (
                    "date" in column_name
                    or
                    "time" in column_name
                ):

                    converted = (
                        pd.to_datetime(
                            dataframe[column],
                            errors="coerce"
                        )
                    )

                    if (
                        converted.notna().sum()
                        > 0
                    ):

                        dataframe[column] = (
                            converted
                            .dt.strftime(
                                "%Y-%m-%d"
                            )
                        )

            actions.append(
                "Converted date/time columns to standard date format"
            )

        # ----------------------------------------------------
        # NO ACTION
        # ----------------------------------------------------

        if not actions:

            messages.warning(
                request,
                (
                    "Please select at least "
                    "one transformation."
                )
            )

            return redirect(
                f"/data/transformation/"
                f"?dataset={dataset.id}"
            )

        # ----------------------------------------------------
        # DOWNLOAD
        # ----------------------------------------------------

        response = HttpResponse(
            content_type="text/csv"
        )

        safe_name = (
            dataset.name
            .replace(" ", "_")
            .replace("/", "_")
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="transformed_'
            f'{safe_name}.csv"'
        )

        dataframe.to_csv(
            response,
            index=False
        )

        return response

    except Exception as error:

        messages.error(
            request,
            (
                "Transformation failed: "
                f"{error}"
            )
        )

        return redirect(
            "data_management:data_transformation"
        )


# ============================================================
# DATA VERSION HISTORY
# ============================================================

@login_required
def data_version_history(request):

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

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True
    )

    selected_dataset = None
    versions = []

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

    return render(
        request,
        "data_management/data_version_history.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "versions":
                versions,
        }
    )


# ============================================================
# DOWNLOAD DATASET VERSION
# ============================================================

@login_required
def download_dataset_version(
    request,
    version_id
):

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

    version = (
        DatasetVersion.objects
        .filter(
            id=version_id,
            dataset__owner=request.user,
            dataset__is_active=True
        )
        .select_related(
            "dataset"
        )
        .first()
    )

    if version is None:

        messages.error(
            request,
            "Dataset version not found."
        )

        return redirect(
            "data_management:data_version_history"
        )

    try:

        original_filename = (
            version.file_name
            or ""
        )

        extension = os.path.splitext(
            original_filename
        )[1].lower()

        if extension == ".xlsx":

            content_type = (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )

        elif extension == ".xls":

            content_type = (
                "application/vnd.ms-excel"
            )

        else:

            content_type = "text/csv"

        file_handle = (
            version.file.open("rb")
        )

        response = HttpResponse(
            file_handle,
            content_type=content_type
        )

        safe_name = (
            version.dataset.name
            .replace(" ", "_")
            .replace("/", "_")
        )

        final_extension = (
            extension
            if extension
            else ".csv"
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{safe_name}_'
            f'v{version.version_number}'
            f'{final_extension}"'
        )

        return response

    except Exception as error:

        messages.error(
            request,
            (
                "Unable to download version: "
                f"{error}"
            )
        )

        return redirect(
            "data_management:data_version_history"
        )


# ============================================================
# DELETE / ARCHIVE DATASET
# ============================================================

@login_required
def delete_dataset(
    request,
    dataset_id
):

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

    dataset = (
        Dataset.objects
        .filter(
            id=dataset_id,
            owner=request.user,
            is_active=True
        )
        .first()
    )

    if dataset is None:

        messages.error(
            request,
            "Dataset not found."
        )

        return redirect(
            "data_management:dataset_management"
        )

    if request.method == "POST":

        dataset.is_active = False

        dataset.save(
            update_fields=[
                "is_active",
                "updated_at"
            ]
        )

        messages.success(
            request,
            (
                f"{dataset.name} has been archived "
                "successfully."
            )
        )

        return redirect(
            "data_management:dataset_management"
        )

    return render(
        request,
        "data_management/delete_dataset.html",
        {
            "dataset":
                dataset
        }
    )