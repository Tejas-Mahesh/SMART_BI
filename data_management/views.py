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
from io import StringIO
from django.core.files.base import ContentFile
# ============================================================
# COMMON APPROVAL CHECK
# ============================================================
# ============================================================
# READ DATASET VERSION FILE
# ============================================================
def read_dataset_version_file(version):

    if version is None:
        raise ValueError(
            "Dataset version was not provided."
        )

    if not version.file:
        raise ValueError(
            "Dataset version does not contain a file."
        )

    file_name = (
        version.file_name
        or version.file.name
        or ""
    )

    extension = os.path.splitext(
        file_name
    )[1].lower()

    version.file.open("rb")

    try:

        if extension == ".csv":

            dataframe = pd.read_csv(
                version.file
            )

        elif extension in [".xlsx", ".xls"]:

            dataframe = pd.read_excel(
                version.file
            )

        else:

            raise ValueError(
                (
                    "Unsupported dataset format: "
                    f"{extension or 'unknown'}"
                )
            )

    finally:

        version.file.close()

    if dataframe is None:
        raise ValueError(
            "Unable to read dataset version."
        )

    return dataframe
def user_is_approved(request):
    """
    Check whether the current user is authenticated
    and has been approved by the administrator.
    """

    if not request.user.is_authenticated:
        return False

    return getattr(
        request.user,
        "approval_status",
        ""
    ) == "Approved"


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

    Returns:
        Float between 0 and 100.
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

# ============================================================
# CREATE ORIGINAL DATASET VERSION
# ============================================================

def create_original_dataset_version(dataset):
    """
    Create Version 1 for the uploaded dataset.

    Version 1 always represents the original uploaded file.
    """

    # --------------------------------------------------------
    # Check whether Version 1 already exists
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Make sure no other version is marked current
    # --------------------------------------------------------

    DatasetVersion.objects.filter(
        dataset=dataset,
        is_current=True
    ).update(
        is_current=False
    )

    # --------------------------------------------------------
    # Validate original file
    # --------------------------------------------------------

    if not dataset.file:
        raise ValueError(
            "Cannot create original dataset version "
            "because the dataset file is missing."
        )

    # --------------------------------------------------------
    # Create Version 1
    # --------------------------------------------------------

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
    Version 2+ = Cleaned / subsequent processing versions.
    """

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if cleaned_dataframe is None:
        raise ValueError(
            "Cleaned dataframe is missing."
        )

    # --------------------------------------------------------
    # Determine next version number
    # --------------------------------------------------------

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
            latest_version.version_number + 1
        )
    else:
        next_version = 1

    # --------------------------------------------------------
    # Calculate cleaned statistics
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Convert cleaned dataframe to CSV
    # --------------------------------------------------------

    csv_content = (
        cleaned_dataframe
        .to_csv(index=False)
    )

    csv_bytes = (
        csv_content.encode("utf-8")
    )

    # --------------------------------------------------------
    # Safe filename
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Make previous current version inactive
    # --------------------------------------------------------

    DatasetVersion.objects.filter(
        dataset=dataset,
        is_current=True
    ).update(
        is_current=False
    )

    # --------------------------------------------------------
    # Create cleaned version
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # Save physical cleaned file
    # --------------------------------------------------------

    version.file.save(
        cleaned_filename,
        ContentFile(csv_bytes),
        save=False
    )

    version.file_size = (
        version.file.size
        if version.file
        else len(csv_bytes)
    )

    version.save()

    # --------------------------------------------------------
    # Update Dataset metadata
    # --------------------------------------------------------

    dataset.total_rows = cleaned_rows

    dataset.total_columns = cleaned_columns

    dataset.missing_values = missing_after

    dataset.duplicate_rows = duplicates_after

    dataset.quality_score = cleaned_quality_score

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

                dataset.total_rows = total_rows

                dataset.total_columns = total_columns

                dataset.missing_values = missing_values

                dataset.duplicate_rows = duplicate_rows

                dataset.quality_score = quality_score

                # Important: save the uploaded file as well.
                uploaded_file.seek(0)

                dataset.file = uploaded_file

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
                    for column in dataframe.columns
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
                    for column in
                    dataframe
                    .select_dtypes(
                        include="number"
                    )
                    .columns
                ]

                categorical_columns = [
                    str(column)
                    for column in
                    dataframe
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
                    - final_rows
                )

                # =================================================
                # 10A. CREATE ORIGINAL VERSION FIRST
                # =================================================

                original_version = (
                    create_original_dataset_version(
                        dataset
                    )
                )

                if original_version is None:

                    raise ValueError(
                        "Smart BI could not create "
                        "the original dataset version."
                    )

                # =================================================
                # 10B. CREATE CLEANED VERSION
                # =================================================

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

# ============================================================
# DATASET PREVIEW
# ============================================================

@login_required
def dataset_preview(request, dataset_id):

    # ---------------------------------------------------------
    # APPROVAL CHECK
    # ---------------------------------------------------------

    if not user_is_approved(request):
        return redirect("accounts:login")

    # ---------------------------------------------------------
    # GET DATASET
    # ---------------------------------------------------------

    dataset = (
        Dataset.objects
        .filter(
            id=dataset_id,
            owner=request.user,
            is_active=True
        )
        .first()
    )

    if not dataset:
        messages.error(
            request,
            "Dataset not found."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # GET ALL VERSIONS
    # ---------------------------------------------------------

    versions = list(
        DatasetVersion.objects
        .filter(
            dataset=dataset
        )
        .order_by(
            "-version_number"
        )
    )

    # ---------------------------------------------------------
    # SELECT REQUESTED VERSION
    # ---------------------------------------------------------

    version_id = request.GET.get("version")

    selected_version = None

    if version_id:

        try:

            selected_version = (
                DatasetVersion.objects
                .filter(
                    id=version_id,
                    dataset=dataset
                )
                .first()
            )

        except (ValueError, TypeError):

            selected_version = None

    # ---------------------------------------------------------
    # DEFAULT = CURRENT VERSION
    # ---------------------------------------------------------

    if selected_version is None:

        selected_version = next(
            (
                version
                for version in versions
                if version.is_current
            ),
            None
        )

    # ---------------------------------------------------------
    # FALLBACK = LATEST VERSION
    # ---------------------------------------------------------

    if selected_version is None and versions:

        selected_version = versions[0]

    # ---------------------------------------------------------
    # FALLBACK = DATASET FILE
    # ---------------------------------------------------------

    file_to_read = None

    if (
        selected_version
        and selected_version.file
    ):

        file_to_read = selected_version.file

    elif dataset.file:

        file_to_read = dataset.file

    if not file_to_read:

        messages.error(
            request,
            "Dataset file could not be found."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # READ DATAFRAME
    # ---------------------------------------------------------

    dataframe = None

    try:

        # -----------------------------------------------------
        # Determine filename
        # -----------------------------------------------------

        filename = ""

        if selected_version:

            filename = (
                selected_version.file_name
                or ""
            )

        if not filename:

            filename = (
                dataset.original_filename
                or (
                    dataset.file.name
                    if dataset.file
                    else ""
                )
                or ""
            )

        filename_lower = filename.lower()

        # -----------------------------------------------------
        # Open Django FileField
        # -----------------------------------------------------

        file_to_read.open("rb")

        try:

            if filename_lower.endswith(".csv"):

                dataframe = pd.read_csv(
                    file_to_read
                )

            elif filename_lower.endswith(".xlsx"):

                dataframe = pd.read_excel(
                    file_to_read,
                    engine="openpyxl"
                )

            elif filename_lower.endswith(".xls"):

                dataframe = pd.read_excel(
                    file_to_read
                )

            else:

                messages.error(
                    request,
                    (
                        "Unsupported file format: "
                        f"{filename}"
                    )
                )

                return redirect(
                    "data_management:dataset_management"
                )

        finally:

            file_to_read.close()

    except Exception as error:

        try:
            file_to_read.close()
        except Exception:
            pass

        messages.error(
            request,
            (
                "Unable to read dataset: "
                f"{error}"
            )
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # HANDLE EMPTY DATAFRAME
    # ---------------------------------------------------------

    if dataframe is None:

        messages.error(
            request,
            "Unable to load dataset."
        )

        return redirect(
            "data_management:dataset_management"
        )

    # ---------------------------------------------------------
    # PREPARE PREVIEW
    # ---------------------------------------------------------

    dataframe = dataframe.fillna("")

    preview_dataframe = dataframe.head(20)

    columns = [
        str(column)
        for column in preview_dataframe.columns
    ]

    rows = []

    for _, row in preview_dataframe.iterrows():

        rows.append(
            [
                str(value)
                for value in row.tolist()
            ]
        )

    # ---------------------------------------------------------
    # VERSION LABELS
    # ---------------------------------------------------------

    if selected_version:

        version_type = (
            selected_version.version_type
            or "Unknown"
        )

        if version_type == "Cleaned":

            version_label = (
                "Cleaned Dataset"
            )

            version_badge = (
                "Analytics Ready"
            )

        elif version_type == "Original":

            version_label = (
                "Original Uploaded Data"
            )

            version_badge = "Original"

        elif version_type == "Transformed":

            version_label = (
                "Transformed Dataset"
            )

            version_badge = "Transformed"

        else:

            version_label = (
                f"Version "
                f"{selected_version.version_number}"
            )

            version_badge = version_type

    else:

        version_label = (
            "Uploaded Data"
        )

        version_badge = "Original"

    # ---------------------------------------------------------
    # ORIGINAL VERSION
    # ---------------------------------------------------------

    original_version = next(
        (
            version
            for version in versions
            if version.version_type == "Original"
        ),
        None
    )

    # ---------------------------------------------------------
    # CURRENT VERSION
    # ---------------------------------------------------------

    current_version = next(
        (
            version
            for version in versions
            if version.is_current
        ),
        None
    )

    # ---------------------------------------------------------
    # CURRENT CLEANED VERSION
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # CURRENT TRANSFORMED VERSION
    # ---------------------------------------------------------

    transformed_version = next(
        (
            version
            for version in versions
            if (
                version.version_type == "Transformed"
                and version.is_current
            )
        ),
        None
    )

    # ---------------------------------------------------------
    # VERSION STATUS
    # ---------------------------------------------------------

    is_original = (
        selected_version is not None
        and selected_version.version_type
        == "Original"
    )

    is_cleaned = (
        selected_version is not None
        and selected_version.version_type
        == "Cleaned"
    )

    is_transformed = (
        selected_version is not None
        and selected_version.version_type
        == "Transformed"
    )

    # ---------------------------------------------------------
    # CONTEXT
    # ---------------------------------------------------------

    context = {

        "dataset":
            dataset,

        "version":
            selected_version,

        "selected_version":
            selected_version,

        "current_version":
            current_version,

        "version_label":
            version_label,

        "version_badge":
            version_badge,

        "versions":
            versions,

        "columns":
            columns,

        "rows":
            rows,

        "preview_rows":
            len(rows),

        "total_rows":
            (
                selected_version.total_rows
                if selected_version
                else len(dataframe)
            ),

        "total_columns":
            (
                selected_version.total_columns
                if selected_version
                else len(dataframe.columns)
            ),

        "missing_values":
            (
                selected_version.missing_values
                if selected_version
                else int(
                    dataframe
                    .isna()
                    .sum()
                    .sum()
                )
            ),

        "duplicate_rows":
            (
                selected_version.duplicate_rows
                if selected_version
                else int(
                    dataframe
                    .duplicated()
                    .sum()
                )
            ),

        "quality_score":
            (
                selected_version.quality_score
                if selected_version
                else dataset.quality_score
            ),

        "is_original":
            is_original,

        "is_cleaned":
            is_cleaned,

        "is_transformed":
            is_transformed,

        "original_version":
            original_version,

        "cleaned_version":
            cleaned_version,

        "transformed_version":
            transformed_version,
    }

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # APPROVAL CHECK
    # ---------------------------------------------------------

    if not user_is_approved(request):
        return redirect("accounts:login")

    # ---------------------------------------------------------
    # GET USER DATASETS
    # ---------------------------------------------------------

    datasets = (
        Dataset.objects
        .filter(
            owner=request.user,
            is_active=True
        )
        .prefetch_related(
            Prefetch(
                "activities",
                queryset=(
                    DatasetActivity.objects
                    .order_by("-created_at")
                )
            ),
            Prefetch(
                "versions",
                queryset=(
                    DatasetVersion.objects
                    .order_by("-version_number")
                )
            )
        )
        .order_by("-uploaded_at")
    )

    # ---------------------------------------------------------
    # PREPARE DATA FOR EACH DATASET
    # ---------------------------------------------------------

    for dataset in datasets:

        versions = list(
            dataset.versions.all()
        )

        # -----------------------------------------------------
        # ORIGINAL VERSION
        # -----------------------------------------------------

        original_version = next(
            (
                version
                for version in versions
                if version.version_type == "Original"
            ),
            None
        )

        # -----------------------------------------------------
        # CURRENT VERSION
        # -----------------------------------------------------

        current_version = next(
            (
                version
                for version in versions
                if version.is_current
            ),
            None
        )

        # -----------------------------------------------------
        # FALLBACK = LATEST VERSION
        # -----------------------------------------------------

        if current_version is None and versions:

            current_version = versions[0]

        # -----------------------------------------------------
        # CURRENT CLEANED VERSION
        # -----------------------------------------------------

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

        # -----------------------------------------------------
        # FALLBACK = LATEST CLEANED VERSION
        # -----------------------------------------------------

        if cleaned_version is None:

            cleaned_versions = [
                version
                for version in versions
                if version.version_type == "Cleaned"
            ]

            if cleaned_versions:

                cleaned_version = max(
                    cleaned_versions,
                    key=lambda version:
                    version.version_number
                )

        # -----------------------------------------------------
        # CURRENT TRANSFORMED VERSION
        # -----------------------------------------------------

        transformed_version = next(
            (
                version
                for version in versions
                if (
                    version.version_type == "Transformed"
                    and version.is_current
                )
            ),
            None
        )

        # -----------------------------------------------------
        # FALLBACK = LATEST TRANSFORMED VERSION
        # -----------------------------------------------------

        if transformed_version is None:

            transformed_versions = [
                version
                for version in versions
                if version.version_type == "Transformed"
            ]

            if transformed_versions:

                transformed_version = max(
                    transformed_versions,
                    key=lambda version:
                    version.version_number
                )

        # -----------------------------------------------------
        # ATTACH VERSION INFORMATION
        # -----------------------------------------------------

        dataset.original_version = (
            original_version
        )

        dataset.current_version = (
            current_version
        )

        dataset.cleaned_version = (
            cleaned_version
        )

        dataset.transformed_version = (
            transformed_version
        )

        # -----------------------------------------------------
        # CURRENT VERSION INFORMATION
        # -----------------------------------------------------

        if current_version:

            dataset.current_version_number = (
                current_version.version_number
            )

            dataset.current_version_type = (
                current_version.version_type
            )

            dataset.current_quality_score = (
                current_version.quality_score
            )

            dataset.current_rows = (
                current_version.total_rows
            )

            dataset.current_columns = (
                current_version.total_columns
            )

            dataset.current_missing_values = (
                current_version.missing_values
            )

            dataset.current_duplicate_rows = (
                current_version.duplicate_rows
            )

        else:

            dataset.current_version_number = None

            dataset.current_version_type = (
                "Original"
            )

            dataset.current_quality_score = (
                dataset.quality_score
            )

            dataset.current_rows = (
                dataset.total_rows
            )

            dataset.current_columns = (
                dataset.total_columns
            )

            dataset.current_missing_values = (
                dataset.missing_values
            )

            dataset.current_duplicate_rows = (
                dataset.duplicate_rows
            )

        # -----------------------------------------------------
        # PROCESSING STATUS
        # -----------------------------------------------------

        if current_version:

            if current_version.version_type == "Original":

                dataset.processing_status = (
                    "Original"
                )

            elif current_version.version_type == "Cleaned":

                dataset.processing_status = (
                    "Analytics Ready"
                )

            elif current_version.version_type == "Transformed":

                dataset.processing_status = (
                    "Transformed"
                )

            else:

                dataset.processing_status = (
                    current_version.version_type
                )

        else:

            dataset.processing_status = (
                "Processing"
            )

        # -----------------------------------------------------
        # VERSION COUNT
        # -----------------------------------------------------

        dataset.version_count = len(
            versions
        )

        # -----------------------------------------------------
        # LAST VERSION
        # -----------------------------------------------------

        dataset.latest_version = (
            versions[0]
            if versions
            else None
        )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------

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

    # --------------------------------------------------------
    # ACCESS CONTROL
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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    quality_data = None

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

    elif datasets.exists():
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------
    if selected_dataset:

        versions = list(
            selected_dataset.versions
            .all()
            .order_by("-version_number")
        )

        version_id = request.GET.get("version")

        # Explicit version selected from UI
        if version_id:
            selected_version = next(
                (
                    version
                    for version in versions
                    if str(version.id) == str(version_id)
                ),
                None
            )

        # Otherwise use current version
        if selected_version is None:
            selected_version = next(
                (
                    version
                    for version in versions
                    if version.is_current
                ),
                None
            )

        # If no current version exists, use latest version
        if selected_version is None and versions:
            selected_version = versions[0]

    # --------------------------------------------------------
    # ANALYZE DATASET
    # --------------------------------------------------------
    if selected_dataset:

        try:

            # ------------------------------------------------
            # READ THE SELECTED VERSION
            # ------------------------------------------------
            if selected_version and selected_version.file:
                dataframe = read_dataset_file(
                    selected_version
                )
            else:
                dataframe = read_dataset_file(
                    selected_dataset
                )

            # ------------------------------------------------
            # BASIC DATASET INFORMATION
            # ------------------------------------------------
            total_rows = int(
                len(dataframe)
            )

            total_columns = int(
                len(dataframe.columns)
            )

            # ------------------------------------------------
            # EMPTY DATASET PROTECTION
            # ------------------------------------------------
            if total_rows == 0 or total_columns == 0:

                missing_values = 0
                duplicate_rows = 0
                complete_rows = 0
                incomplete_rows = 0
                missing_percentage = 0
                duplicate_percentage = 0

            else:

                # --------------------------------------------
                # MISSING VALUES
                # --------------------------------------------
                missing_values = int(
                    dataframe
                    .isnull()
                    .sum()
                    .sum()
                )

                # --------------------------------------------
                # DUPLICATE ROWS
                # --------------------------------------------
                duplicate_rows = int(
                    dataframe
                    .duplicated()
                    .sum()
                )

                # --------------------------------------------
                # ROW COMPLETENESS
                # --------------------------------------------
                incomplete_rows = int(
                    dataframe
                    .isnull()
                    .any(axis=1)
                    .sum()
                )

                complete_rows = (
                    total_rows
                    - incomplete_rows
                )

                # --------------------------------------------
                # MISSING PERCENTAGE
                # --------------------------------------------
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
                )

                # --------------------------------------------
                # DUPLICATE PERCENTAGE
                # --------------------------------------------
                duplicate_percentage = round(
                    (
                        duplicate_rows
                        /
                        total_rows
                    )
                    * 100,
                    2
                )

            # ------------------------------------------------
            # QUALITY SCORE
            # ------------------------------------------------
            quality_score = calculate_quality_score(
                dataframe,
                missing_values,
                duplicate_rows
            )

            # Make sure score remains usable in templates
            quality_score = round(
                float(quality_score),
                2
            )

            # ------------------------------------------------
            # OVERALL QUALITY STATUS
            # ------------------------------------------------
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

            # ------------------------------------------------
            # COLUMN-LEVEL QUALITY
            # ------------------------------------------------
            column_quality = []

            for column in dataframe.columns:

                series = dataframe[column]

                # --------------------------------------------
                # COLUMN MISSING VALUES
                # --------------------------------------------
                column_missing = int(
                    series.isnull().sum()
                )

                # --------------------------------------------
                # COLUMN MISSING PERCENTAGE
                # --------------------------------------------
                column_missing_percentage = round(
                    (
                        column_missing
                        /
                        total_rows
                    )
                    * 100,
                    2
                ) if total_rows else 0

                # --------------------------------------------
                # COLUMN DUPLICATES
                # --------------------------------------------
                column_duplicates = int(
                    series.duplicated().sum()
                )

                # --------------------------------------------
                # NON-NULL VALUES
                # --------------------------------------------
                non_null_values = int(
                    series.notnull().sum()
                )

                # --------------------------------------------
                # COLUMN QUALITY STATUS
                # --------------------------------------------
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

                # --------------------------------------------
                # COLUMN QUALITY OBJECT
                # --------------------------------------------
                column_quality.append(
                    {
                        "name": str(column),

                        "data_type": str(
                            series.dtype
                        ),

                        "missing": column_missing,

                        "missing_percentage":
                            column_missing_percentage,

                        "non_null":
                            non_null_values,

                        "duplicates":
                            column_duplicates,

                        "unique_values": int(
                            series.nunique(
                                dropna=True
                            )
                        ),

                        "status":
                            column_status,

                        "status_class":
                            column_class,
                    }
                )

            # ------------------------------------------------
            # VERSION INFORMATION
            # ------------------------------------------------
            version_label = "Dataset File"
            version_badge = "dataset"

            if selected_version:

                version_type = (
                    selected_version.version_type
                    or "Original"
                )

                version_label = (
                    f"Version "
                    f"{selected_version.version_number}"
                    f" — "
                    f"{version_type}"
                )

                if version_type.lower() == "original":

                    version_badge = "original"

                elif version_type.lower() == "cleaned":

                    version_badge = "cleaned"

                elif version_type.lower() == "transformed":

                    version_badge = "transformed"

                else:

                    version_badge = "version"

            # ------------------------------------------------
            # QUALITY DATA FOR TEMPLATE
            # ------------------------------------------------
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

                "version_label":
                    version_label,

                "version_badge":
                    version_badge,

                "version_number":
                    (
                        selected_version.version_number
                        if selected_version
                        else None
                    ),

                "version_type":
                    (
                        selected_version.version_type
                        if selected_version
                        else None
                    ),

                "is_original":
                    (
                        selected_version.version_type
                        == "Original"
                        if selected_version
                        else False
                    ),

                "is_cleaned":
                    (
                        selected_version.version_type
                        == "Cleaned"
                        if selected_version
                        else False
                    ),

                "is_transformed":
                    (
                        selected_version.version_type
                        == "Transformed"
                        if selected_version
                        else False
                    ),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to analyze dataset: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------------
    context = {

        "datasets":
            datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            selected_version,

        "quality":
            quality_data,
    }

    return render(
        request,
        "data_management/data_quality.html",
        context
    )


# ============================================================
# DATA CLEANING
# ============================================================

@login_required
def data_cleaning(request):

    # --------------------------------------------------------
    # ACCESS CONTROL
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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    cleaning_data = None

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

    elif datasets.exists():
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------
    if selected_dataset:

        versions = list(
            selected_dataset.versions
            .all()
            .order_by("-version_number")
        )

        version_id = request.GET.get("version")

        # Explicit version selected
        if version_id:

            selected_version = next(
                (
                    version
                    for version in versions
                    if str(version.id) == str(version_id)
                ),
                None
            )

        # Otherwise use current version
        if selected_version is None:

            selected_version = next(
                (
                    version
                    for version in versions
                    if version.is_current
                ),
                None
            )

        # Fallback to latest version
        if selected_version is None and versions:

            selected_version = versions[0]

    # --------------------------------------------------------
    # ANALYZE / PREVIEW CLEANING
    # --------------------------------------------------------
    if selected_dataset:

        try:

            # ------------------------------------------------
            # READ SELECTED VERSION
            # ------------------------------------------------
            if selected_version and selected_version.file:

                dataframe = read_dataset_file(
                    selected_version
                )

            else:

                dataframe = read_dataset_file(
                    selected_dataset
                )

            # ------------------------------------------------
            # BEFORE CLEANING
            # ------------------------------------------------
            before_rows = int(
                len(dataframe)
            )

            before_columns = int(
                len(dataframe.columns)
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

            # ------------------------------------------------
            # EMPTY ROWS
            # ------------------------------------------------
            empty_rows = int(
                dataframe
                .isnull()
                .all(axis=1)
                .sum()
            )

            # Remove completely empty rows
            dataframe = dataframe.dropna(
                how="all"
            ).copy()

            # ------------------------------------------------
            # TEXT CLEANING
            # ------------------------------------------------
            text_columns_cleaned = 0
            text_values_cleaned = 0

            for column in dataframe.columns:

                # Handle pandas string/object columns
                if (
                    dataframe[column].dtype == "object"
                    or str(
                        dataframe[column].dtype
                    ).startswith("string")
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

                    changed_values = int(
                        (
                            original_values
                            !=
                            dataframe[column]
                        )
                        .fillna(False)
                        .sum()
                    )

                    if changed_values > 0:

                        text_columns_cleaned += 1

                        text_values_cleaned += (
                            changed_values
                        )

            # ------------------------------------------------
            # DUPLICATE ROWS
            # ------------------------------------------------
            duplicates_removed = int(
                dataframe
                .duplicated()
                .sum()
            )

            dataframe = (
                dataframe
                .drop_duplicates()
                .copy()
            )

            # ------------------------------------------------
            # AFTER CLEANING
            # ------------------------------------------------
            after_missing = int(
                dataframe
                .isnull()
                .sum()
                .sum()
            )

            after_rows = int(
                len(dataframe)
            )

            after_columns = int(
                len(dataframe.columns)
            )

            after_duplicates = int(
                dataframe
                .duplicated()
                .sum()
            )

            # ------------------------------------------------
            # IMPROVEMENT METRICS
            # ------------------------------------------------
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

            duplicate_reduction = (
                before_duplicates
                -
                after_duplicates
            )

            # Number of categories of cleaning actions
            total_cleaning_actions = (
                int(empty_rows > 0)
                +
                int(duplicates_removed > 0)
                +
                text_columns_cleaned
            )

            # ------------------------------------------------
            # CLEANING PERCENTAGE
            # ------------------------------------------------
            if before_rows > 0:

                rows_retained_percentage = round(
                    (
                        after_rows
                        /
                        before_rows
                    )
                    * 100,
                    2
                )

            else:

                rows_retained_percentage = 0

            if before_missing > 0:

                missing_reduction_percentage = round(
                    (
                        missing_reduction
                        /
                        before_missing
                    )
                    * 100,
                    2
                )

            else:

                missing_reduction_percentage = 0

            if before_duplicates > 0:

                duplicate_reduction_percentage = round(
                    (
                        duplicate_reduction
                        /
                        before_duplicates
                    )
                    * 100,
                    2
                )

            else:

                duplicate_reduction_percentage = 0

            # ------------------------------------------------
            # VERSION INFORMATION
            # ------------------------------------------------
            version_label = "Dataset File"
            version_badge = "dataset"

            if selected_version:

                version_type = (
                    selected_version.version_type
                    or "Original"
                )

                version_label = (
                    f"Version "
                    f"{selected_version.version_number}"
                    f" — "
                    f"{version_type}"
                )

                version_type_lower = (
                    version_type.lower()
                )

                if version_type_lower == "original":

                    version_badge = "original"

                elif version_type_lower == "cleaned":

                    version_badge = "cleaned"

                elif version_type_lower == "transformed":

                    version_badge = "transformed"

                else:

                    version_badge = "version"

            # ------------------------------------------------
            # CLEANING RESULT
            # ------------------------------------------------
            cleaning_data = {

                # Before
                "before_rows":
                    before_rows,

                "before_columns":
                    before_columns,

                "before_missing":
                    before_missing,

                "before_duplicates":
                    before_duplicates,

                # After
                "after_rows":
                    after_rows,

                "after_columns":
                    after_columns,

                "after_missing":
                    after_missing,

                "after_duplicates":
                    after_duplicates,

                # Actions
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

                "text_values_cleaned":
                    text_values_cleaned,

                "duplicate_reduction":
                    duplicate_reduction,

                "total_actions":
                    total_cleaning_actions,

                # Percentages
                "rows_retained_percentage":
                    rows_retained_percentage,

                "missing_reduction_percentage":
                    missing_reduction_percentage,

                "duplicate_reduction_percentage":
                    duplicate_reduction_percentage,

                # Version
                "version_label":
                    version_label,

                "version_badge":
                    version_badge,

                "version_number":
                    (
                        selected_version.version_number
                        if selected_version
                        else None
                    ),

                "version_type":
                    (
                        selected_version.version_type
                        if selected_version
                        else None
                    ),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to analyze dataset for cleaning: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------------
    context = {

        "datasets":
            datasets,

        "selected_dataset":
            selected_dataset,

        "selected_version":
            selected_version,

        "cleaning":
            cleaning_data,
    }

    return render(
        request,
        "data_management/data_cleaning.html",
        context
    )

# ============================================================
# DOWNLOAD CLEANED DATASET
# ============================================================

@login_required
def download_cleaned_dataset(
    request,
    dataset_id
):

    # --------------------------------------------------------
    # ACCESS CONTROL
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
    # GET USER'S DATASET
    # --------------------------------------------------------
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
    # FIND LATEST CLEANED VERSION
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

    # --------------------------------------------------------
    # CHECK CLEANED FILE
    # --------------------------------------------------------
    if not cleaned_version.file:

        messages.error(
            request,
            "The cleaned dataset file is not available."
        )

        return redirect(
            "data_management:data_cleaning"
        )

    # --------------------------------------------------------
    # DOWNLOAD FILE
    # --------------------------------------------------------
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

        # ----------------------------------------------------
        # SAFE DOWNLOAD NAME
        # ----------------------------------------------------
        safe_name = (
            dataset.name
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace('"', "")
        )

        filename = (
            f"{safe_name}_"
            f"cleaned_v"
            f"{cleaned_version.version_number}"
            f".csv"
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{filename}"'
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

    # --------------------------------------------------------
    # ACCESS CONTROL
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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    validation = None

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

    elif datasets.exists():

        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------
    if selected_dataset:

        versions = list(
            selected_dataset.versions
            .all()
            .order_by("-version_number")
        )

        version_id = request.GET.get("version")

        # Explicit version selected
        if version_id:

            selected_version = next(
                (
                    version
                    for version in versions
                    if str(version.id) == str(version_id)
                ),
                None
            )

        # Use current version if no explicit version
        if selected_version is None:

            selected_version = next(
                (
                    version
                    for version in versions
                    if version.is_current
                ),
                None
            )

        # Fallback to latest version
        if selected_version is None and versions:

            selected_version = versions[0]

    # --------------------------------------------------------
    # VALIDATE SELECTED DATASET
    # --------------------------------------------------------
    if selected_dataset:

        try:

            # ------------------------------------------------
            # READ SELECTED VERSION
            # ------------------------------------------------
            if selected_version and selected_version.file:

                dataframe = read_dataset_file(
                    selected_version
                )

            else:

                dataframe = read_dataset_file(
                    selected_dataset
                )

            # ------------------------------------------------
            # NORMALIZE COLUMN NAMES
            # ------------------------------------------------
            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

            columns = list(
                dataframe.columns
            )

            # Case-insensitive column lookup
            lower_columns = {
                str(column).strip().lower(): column
                for column in columns
            }

            total_rows = int(
                len(dataframe)
            )

            total_columns = int(
                len(dataframe.columns)
            )

            # ------------------------------------------------
            # DATASET TYPE
            # ------------------------------------------------
            dataset_type = (
                selected_dataset.dataset_type
                or ""
            )

            # ------------------------------------------------
            # REQUIRED COLUMNS
            # ------------------------------------------------
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

            # ------------------------------------------------
            # FIND MISSING REQUIRED COLUMNS
            # ------------------------------------------------
            missing_required_columns = []

            for required_column in required_columns:

                if (
                    required_column.lower()
                    not in lower_columns
                ):

                    missing_required_columns.append(
                        required_column.title()
                    )

            # ------------------------------------------------
            # COLUMN FINDER
            # ------------------------------------------------
            def find_column(possible_names):

                for name in possible_names:

                    normalized_name = (
                        str(name)
                        .strip()
                        .lower()
                    )

                    if normalized_name in lower_columns:

                        return lower_columns[
                            normalized_name
                        ]

                return None

            # ------------------------------------------------
            # DETECT IMPORTANT COLUMNS
            # ------------------------------------------------
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
            # VALIDATION CONTAINERS
            # ------------------------------------------------
            validation_errors = []

            row_failed_flags = []

            # ------------------------------------------------
            # DUPLICATE ROW DETECTION
            # ------------------------------------------------
            duplicate_mask = (
                dataframe
                .duplicated(
                    keep=False
                )
            )

            duplicate_rows = int(
                dataframe
                .duplicated()
                .sum()
            )

            # ------------------------------------------------
            # EMPTY ROW DETECTION
            # ------------------------------------------------
            empty_rows = int(
                dataframe
                .isnull()
                .all(axis=1)
                .sum()
            )

            # ------------------------------------------------
            # ROW VALIDATION
            # ------------------------------------------------
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

                    if len(missing_fields) > 5:

                        row_errors.append(
                            f"(+{len(missing_fields) - 5} more)"
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

                # --------------------------------------------
                # ROW RESULT
                # --------------------------------------------
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
            # ROW COUNTS
            # ------------------------------------------------
            failed_rows = int(
                sum(row_failed_flags)
            )

            passed_rows = max(
                0,
                total_rows - failed_rows
            )

            # ------------------------------------------------
            # REQUIRED COLUMN ERROR
            # ------------------------------------------------
            if missing_required_columns:

                validation_errors.insert(
                    0,
                    {
                        "row_number": "-",

                        "reason": (
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
            # VALIDATION SCORE
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

            # Required structural columns are mandatory
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
            # VALIDATION STATUS
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
            # VALIDATION RULE COUNT
            # ------------------------------------------------
            validation_rules = 0

            # Required columns rule
            if required_columns:

                validation_rules += 1

            # Missing-value rule
            validation_rules += 1

            # Duplicate rule
            validation_rules += 1

            # Conditional rules
            if date_column:
                validation_rules += 1

            if sales_column:
                validation_rules += 1

            if quantity_column:
                validation_rules += 1

            if discount_column:
                validation_rules += 1

            # ------------------------------------------------
            # VERSION INFORMATION
            # ------------------------------------------------
            version_label = "Dataset File"
            version_badge = "dataset"

            if selected_version:

                version_type = (
                    selected_version.version_type
                    or "Original"
                )

                version_label = (
                    f"Version "
                    f"{selected_version.version_number}"
                    f" — "
                    f"{version_type}"
                )

                version_type_lower = (
                    version_type.lower()
                )

                if version_type_lower == "original":

                    version_badge = "original"

                elif version_type_lower == "cleaned":

                    version_badge = "cleaned"

                elif version_type_lower == "transformed":

                    version_badge = "transformed"

                else:

                    version_badge = "version"

            # ------------------------------------------------
            # VALIDATION RESULT
            # ------------------------------------------------
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
                    duplicate_rows,

                "duplicate_row_flags":
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

                "version_label":
                    version_label,

                "version_badge":
                    version_badge,

                "version_number":
                    (
                        selected_version.version_number
                        if selected_version
                        else None
                    ),

                "version_type":
                    (
                        selected_version.version_type
                        if selected_version
                        else None
                    ),

                "is_original":
                    (
                        selected_version.version_type
                        == "Original"
                        if selected_version
                        else False
                    ),

                "is_cleaned":
                    (
                        selected_version.version_type
                        == "Cleaned"
                        if selected_version
                        else False
                    ),

                "is_transformed":
                    (
                        selected_version.version_type
                        == "Transformed"
                        if selected_version
                        else False
                    ),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to validate dataset: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # TEMPLATE CONTEXT
    # --------------------------------------------------------
    return render(
        request,
        "data_management/data_validation.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "selected_version":
                selected_version,

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

    # --------------------------------------------------------
    # ACCESS CONTROL
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
    # GET DATASET
    # --------------------------------------------------------
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

        # ----------------------------------------------------
        # FIND VERSION TO VALIDATE
        # ----------------------------------------------------
        versions = list(
            dataset.versions
            .all()
            .order_by("-version_number")
        )

        selected_version = None

        version_id = request.GET.get(
            "version"
        )

        # Explicit version selected
        if version_id:

            selected_version = next(
                (
                    version
                    for version in versions
                    if str(version.id)
                    == str(version_id)
                ),
                None
            )

        # Current version
        if selected_version is None:

            selected_version = next(
                (
                    version
                    for version in versions
                    if version.is_current
                ),
                None
            )

        # Latest version fallback
        if selected_version is None and versions:

            selected_version = versions[0]

        # ----------------------------------------------------
        # READ SELECTED VERSION
        # ----------------------------------------------------
        if (
            selected_version
            and
            selected_version.file
        ):

            dataframe = read_dataset_file(
                selected_version
            )

        else:

            dataframe = read_dataset_file(
                dataset
            )

        # ----------------------------------------------------
        # NORMALIZE COLUMN NAMES
        # ----------------------------------------------------
        dataframe.columns = [
            str(column).strip()
            for column
            in dataframe.columns
        ]

        columns = list(
            dataframe.columns
        )

        lower_columns = {
            str(column).strip().lower():
            column
            for column
            in columns
        }

        # ----------------------------------------------------
        # DATASET TYPE
        # ----------------------------------------------------
        dataset_type = (
            dataset.dataset_type
            or ""
        )

        # ----------------------------------------------------
        # REQUIRED COLUMNS
        # ----------------------------------------------------
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

        for required_column in required_columns:

            if (
                required_column.lower()
                not in lower_columns
            ):

                missing_required_columns.append(
                    required_column.title()
                )

        # ----------------------------------------------------
        # COLUMN FINDER
        # ----------------------------------------------------
        def find_column(possible_names):

            for name in possible_names:

                normalized_name = (
                    str(name)
                    .strip()
                    .lower()
                )

                if normalized_name in lower_columns:

                    return lower_columns[
                        normalized_name
                    ]

            return None

        # ----------------------------------------------------
        # DETECT IMPORTANT COLUMNS
        # ----------------------------------------------------
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

        # ----------------------------------------------------
        # DUPLICATE DETECTION
        # ----------------------------------------------------
        duplicate_mask = (
            dataframe
            .duplicated(
                keep=False
            )
        )

        # ----------------------------------------------------
        # REPORT ROWS
        # ----------------------------------------------------
        report_rows = []

        # ----------------------------------------------------
        # REQUIRED COLUMN ERROR
        # ----------------------------------------------------
        if missing_required_columns:

            report_rows.append(
                {
                    "row_number": "-",

                    "status": "FAILED",

                    "reason": (
                        "Missing required "
                        "column(s): "
                        +
                        ", ".join(
                            missing_required_columns
                        )
                    ),
                }
            )

        # ----------------------------------------------------
        # ROW VALIDATION
        # ----------------------------------------------------
        for position, (
            index,
            row
        ) in enumerate(
            dataframe.iterrows()
        ):

            errors = []

            # ------------------------------------------------
            # Empty row
            # ------------------------------------------------
            if row.isnull().all():

                errors.append(
                    "Empty row"
                )

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

                missing_message = (
                    "Missing value in: "
                    +
                    ", ".join(
                        missing_fields[:5]
                    )
                )

                if len(missing_fields) > 5:

                    missing_message += (
                        f" (+{len(missing_fields) - 5} more)"
                    )

                errors.append(
                    missing_message
                )

            # ------------------------------------------------
            # Date validation
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
            # Sales validation
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
            # Quantity validation
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
            # Discount validation
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
            # Duplicate validation
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

            # ------------------------------------------------
            # REPORT RESULT
            # ------------------------------------------------
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

        # ----------------------------------------------------
        # CREATE REPORT DATAFRAME
        # ----------------------------------------------------
        report_dataframe = pd.DataFrame(
            report_rows,
            columns=[
                "row_number",
                "status",
                "reason",
            ]
        )

        # ----------------------------------------------------
        # CREATE HTTP RESPONSE
        # ----------------------------------------------------
        response = HttpResponse(
            content_type="text/csv"
        )

        # ----------------------------------------------------
        # SAFE FILE NAME
        # ----------------------------------------------------
        safe_name = (
            str(dataset.name)
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace('"', "")
            .replace("'", "")
        )

        # ----------------------------------------------------
        # VERSION-AWARE FILE NAME
        # ----------------------------------------------------
        if selected_version:

            filename = (
                "validation_report_"
                f"{safe_name}_"
                f"v{selected_version.version_number}.csv"
            )

        else:

            filename = (
                "validation_report_"
                f"{safe_name}.csv"
            )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{filename}"'
        )

        # ----------------------------------------------------
        # WRITE CSV
        # ----------------------------------------------------
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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    profiling = None

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

    elif datasets.exists():

        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by("-version_number")
        )

        requested_version = request.GET.get("version")

        # 1. Explicit version selected from URL
        if requested_version:

            selected_version = (
                versions
                .filter(
                    id=requested_version
                )
                .first()
            )

        # 2. Use current version
        if selected_version is None:

            selected_version = (
                versions
                .filter(
                    is_current=True
                )
                .first()
            )

        # 3. Fallback to latest version
        if selected_version is None:

            selected_version = (
                versions
                .first()
            )

        # ----------------------------------------------------
        # READ SELECTED VERSION
        # ----------------------------------------------------

        try:

            if selected_version:

                dataframe = read_dataset_version_file(
                    selected_version
                )

            else:

                dataframe = read_dataset_file(
                    selected_dataset
                )

            # ------------------------------------------------
            # BASIC INFORMATION
            # ------------------------------------------------

            total_rows = len(dataframe)

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
                *
                100
                if total_cells
                else 0
            )

            completeness = round(
                completeness,
                2
            )

            # ------------------------------------------------
            # COLUMN TYPE DETECTION
            # ------------------------------------------------

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

                series = dataframe[column]

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
                    *
                    100
                    if total_rows
                    else 0
                )

                missing_percentage = round(
                    missing_percentage,
                    2
                )

                # --------------------------------------------
                # NUMERIC STATISTICS
                # --------------------------------------------

                minimum = "-"
                maximum = "-"
                mean = "-"
                median = "-"
                standard_deviation = "-"

                if pd.api.types.is_numeric_dtype(
                    series
                ):

                    valid_series = (
                        pd.to_numeric(
                            series,
                            errors="coerce"
                        )
                        .dropna()
                    )

                    if not valid_series.empty:

                        minimum = round(
                            float(
                                valid_series.min()
                            ),
                            2
                        )

                        maximum = round(
                            float(
                                valid_series.max()
                            ),
                            2
                        )

                        mean = round(
                            float(
                                valid_series.mean()
                            ),
                            2
                        )

                        median = round(
                            float(
                                valid_series.median()
                            ),
                            2
                        )

                        standard_deviation = round(
                            float(
                                valid_series.std()
                            )
                            if len(
                                valid_series
                            ) > 1
                            else 0,
                            2
                        )

                # --------------------------------------------
                # TOP CATEGORICAL VALUE
                # --------------------------------------------

                top_value = "-"
                top_frequency = 0

                if (
                    series.dtype == "object"
                    or
                    str(series.dtype) == "category"
                    or
                    str(series.dtype) == "bool"
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

                # --------------------------------------------
                # COLUMN TYPE
                # --------------------------------------------

                if pd.api.types.is_numeric_dtype(
                    series
                ):

                    column_type = "Numeric"
                    type_class = "numeric"

                elif pd.api.types.is_datetime64_any_dtype(
                    series
                ):

                    column_type = "Date / Time"
                    type_class = "datetime"

                else:

                    column_type = "Categorical"
                    type_class = "categorical"

                # --------------------------------------------
                # COLUMN HEALTH
                # --------------------------------------------

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

                # --------------------------------------------
                # SAVE PROFILE
                # --------------------------------------------

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

                series = dataframe[column]

                valid_series = (
                    pd.to_numeric(
                        series,
                        errors="coerce"
                    )
                    .dropna()
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

            # ------------------------------------------------
            # VERSION INFORMATION
            # ------------------------------------------------

            version_label = "Original"
            version_badge = "original"

            if selected_version:

                version_type = (
                    getattr(
                        selected_version,
                        "version_type",
                        ""
                    )
                    or ""
                )

                if version_type.lower() == "cleaned":

                    version_label = "Cleaned"
                    version_badge = "cleaned"

                elif version_type.lower() == "transformed":

                    version_label = "Transformed"
                    version_badge = "transformed"

                elif version_type.lower() == "original":

                    version_label = "Original"
                    version_badge = "original"

                else:

                    version_label = (
                        version_type
                        or
                        f"Version {selected_version.version_number}"
                    )

                    version_badge = "version"

            # ------------------------------------------------
            # FINAL PROFILING OBJECT
            # ------------------------------------------------

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

                # Version information
                "version_number":
                    (
                        selected_version.version_number
                        if selected_version
                        else None
                    ),

                "version_type":
                    (
                        selected_version.version_type
                        if selected_version
                        else "Original"
                    ),

                "version_label":
                    version_label,

                "version_badge":
                    version_badge,

                "is_current":
                    (
                        selected_version.is_current
                        if selected_version
                        else False
                    ),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to profile dataset: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # ALL VERSIONS FOR SELECTED DATASET
    # --------------------------------------------------------

    versions = []

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by("-version_number")
        )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "data_management/data_profiling.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "selected_version":
                selected_version,

            "versions":
                versions,

            "profiling":
                profiling,
        }
    )


# ============================================================
# DATA TRANSFORMATION
# ============================================================

@login_required
def data_transformation(request):

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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    selected_version = None
    transformation = None

    # --------------------------------------------------------
    # DATASET SELECTION
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

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

    # --------------------------------------------------------
    # VERSION SELECTION
    # --------------------------------------------------------

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by("-version_number")
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
        # 3. LATEST VERSION FALLBACK
        # ----------------------------------------------------

        if selected_version is None:

            selected_version = (
                versions
                .first()
            )

        # ----------------------------------------------------
        # LOAD DATASET
        # ----------------------------------------------------

        try:

            if selected_version:

                dataframe = read_dataset_version_file(
                    selected_version
                )

            else:

                dataframe = read_dataset_file(
                    selected_dataset
                )

            # ------------------------------------------------
            # NORMALIZE COLUMN NAMES
            # ------------------------------------------------

            dataframe.columns = [
                str(column).strip()
                for column in dataframe.columns
            ]

            # ------------------------------------------------
            # NUMERIC COLUMNS
            # ------------------------------------------------

            numeric_columns = [
                str(column)
                for column in
                dataframe
                .select_dtypes(
                    include="number"
                )
                .columns
            ]

            # ------------------------------------------------
            # CATEGORICAL COLUMNS
            # ------------------------------------------------

            categorical_columns = [
                str(column)
                for column in
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category",
                        "bool"
                    ]
                )
                .columns
            ]

            # ------------------------------------------------
            # DATE / TIME COLUMNS
            # ------------------------------------------------

            date_columns = []

            for column in dataframe.columns:

                column_name = (
                    str(column)
                    .strip()
                    .lower()
                )

                if (
                    "date" in column_name
                    or
                    "time" in column_name
                ):

                    date_columns.append(
                        str(column)
                    )

            # ------------------------------------------------
            # COLUMN INFORMATION
            # ------------------------------------------------

            column_information = []

            for column in dataframe.columns:

                series = dataframe[column]

                column_information.append(
                    {
                        "name":
                            str(column),

                        "dtype":
                            str(
                                series.dtype
                            ),

                        "missing":
                            int(
                                series
                                .isnull()
                                .sum()
                            ),

                        "unique":
                            int(
                                series
                                .nunique(
                                    dropna=True
                                )
                            ),
                    }
                )

            # ------------------------------------------------
            # VERSION INFORMATION
            # ------------------------------------------------

            version_label = "Original"
            version_badge = "original"

            if selected_version:

                version_type = (
                    getattr(
                        selected_version,
                        "version_type",
                        ""
                    )
                    or ""
                )

                if (
                    version_type
                    .lower()
                    ==
                    "cleaned"
                ):

                    version_label = "Cleaned"
                    version_badge = "cleaned"

                elif (
                    version_type
                    .lower()
                    ==
                    "transformed"
                ):

                    version_label = "Transformed"
                    version_badge = "transformed"

                elif (
                    version_type
                    .lower()
                    ==
                    "original"
                ):

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

            # ------------------------------------------------
            # TRANSFORMATION DATA
            # ------------------------------------------------

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

                "columns":
                    column_information,

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

                # --------------------------------------------
                # VERSION INFORMATION
                # --------------------------------------------

                "version_number":
                    (
                        selected_version.version_number
                        if selected_version
                        else None
                    ),

                "version_type":
                    (
                        selected_version.version_type
                        if selected_version
                        else "Original"
                    ),

                "version_label":
                    version_label,

                "version_badge":
                    version_badge,

                "is_current":
                    (
                        selected_version.is_current
                        if selected_version
                        else False
                    ),
            }

        except Exception as error:

            messages.error(
                request,
                (
                    "Unable to load dataset: "
                    f"{error}"
                )
            )

    # --------------------------------------------------------
    # AVAILABLE VERSIONS
    # --------------------------------------------------------

    versions = []

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by("-version_number")
        )

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "data_management/data_transformation.html",
        {
            "datasets":
                datasets,

            "selected_dataset":
                selected_dataset,

            "selected_version":
                selected_version,

            "versions":
                versions,

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
    # GET DATASET
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # GET SELECTED VERSION
    # --------------------------------------------------------

    requested_version = request.GET.get(
        "version"
    )

    selected_version = None

    versions = (
        DatasetVersion.objects
        .filter(
            dataset=dataset
        )
        .order_by("-version_number")
    )

    # Explicitly selected version
    if requested_version:

        selected_version = (
            versions
            .filter(
                id=requested_version
            )
            .first()
        )

    # Current version fallback
    if selected_version is None:

        selected_version = (
            versions
            .filter(
                is_current=True
            )
            .first()
        )

    # Latest version fallback
    if selected_version is None:

        selected_version = (
            versions
            .first()
        )

    # --------------------------------------------------------
    # PROCESS TRANSFORMATION
    # --------------------------------------------------------

    try:

        # ----------------------------------------------------
        # LOAD SELECTED VERSION
        # ----------------------------------------------------

        if selected_version:

            dataframe = read_dataset_version_file(
                selected_version
            )

        else:

            dataframe = read_dataset_file(
                dataset
            )

        # ----------------------------------------------------
        # COPY DATAFRAME
        # ----------------------------------------------------

        dataframe = dataframe.copy()

        # ----------------------------------------------------
        # NORMALIZE COLUMN NAMES
        # ----------------------------------------------------

        dataframe.columns = [
            str(column).strip()
            for column in dataframe.columns
        ]

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
        # VALIDATE TEXT OPTIONS
        # ----------------------------------------------------

        if lowercase_text and uppercase_text:

            messages.warning(
                request,
                (
                    "Please select either lowercase "
                    "or uppercase text conversion, "
                    "not both."
                )
            )

            return redirect(
                f"/data/transformation/"
                f"?dataset={dataset.id}"
                f"&version={selected_version.id}"
                if selected_version
                else
                f"/data/transformation/"
                f"?dataset={dataset.id}"
            )

        # ----------------------------------------------------
        # VALIDATE NUMERIC OPTIONS
        # ----------------------------------------------------

        if normalize and standardize:

            messages.warning(
                request,
                (
                    "Please select either normalization "
                    "or standardization, not both."
                )
            )

            return redirect(
                f"/data/transformation/"
                f"?dataset={dataset.id}"
                f"&version={selected_version.id}"
                if selected_version
                else
                f"/data/transformation/"
                f"?dataset={dataset.id}"
            )

        # ----------------------------------------------------
        # TRIM TEXT
        # ----------------------------------------------------

        if trim_text:

            text_columns = (
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category"
                    ]
                )
                .columns
            )

            for column in text_columns:

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

            text_columns = (
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category"
                    ]
                )
                .columns
            )

            for column in text_columns:

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

            text_columns = (
                dataframe
                .select_dtypes(
                    include=[
                        "object",
                        "category"
                    ]
                )
                .columns
            )

            for column in text_columns:

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

            filled_columns = []

            for column in numeric_columns:

                if dataframe[
                    column
                ].isnull().any():

                    median_value = (
                        dataframe[column]
                        .median()
                    )

                    if pd.notna(
                        median_value
                    ):

                        dataframe[column] = (
                            dataframe[column]
                            .fillna(
                                median_value
                            )
                        )

                        filled_columns.append(
                            str(column)
                        )

            if filled_columns:

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

            filled_columns = []

            for column in categorical_columns:

                if dataframe[
                    column
                ].isnull().any():

                    mode_values = (
                        dataframe[column]
                        .mode()
                    )

                    if not mode_values.empty:

                        dataframe[column] = (
                            dataframe[column]
                            .fillna(
                                mode_values.iloc[0]
                            )
                        )

                        filled_columns.append(
                            str(column)
                        )

            if filled_columns:

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

            normalized_columns = []

            for column in numeric_columns:

                series = dataframe[column]

                minimum = series.min()
                maximum = series.max()

                if (
                    pd.notna(minimum)
                    and
                    pd.notna(maximum)
                    and
                    maximum != minimum
                ):

                    dataframe[column] = (
                        (
                            series
                            - minimum
                        )
                        /
                        (
                            maximum
                            - minimum
                        )
                    )

                    normalized_columns.append(
                        str(column)
                    )

            if normalized_columns:

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

            standardized_columns = []

            for column in numeric_columns:

                series = dataframe[column]

                mean_value = series.mean()
                std_value = series.std()

                if (
                    pd.notna(std_value)
                    and
                    std_value != 0
                ):

                    dataframe[column] = (
                        (
                            series
                            - mean_value
                        )
                        /
                        std_value
                    )

                    standardized_columns.append(
                        str(column)
                    )

            if standardized_columns:

                actions.append(
                    "Standardized numeric columns using Z-score"
                )

        # ----------------------------------------------------
        # DATE CONVERSION
        # ----------------------------------------------------

        if convert_dates:

            converted_columns = []

            for column in dataframe.columns:

                column_name = (
                    str(column)
                    .strip()
                    .lower()
                )

                if (
                    "date" in column_name
                    or
                    "time" in column_name
                ):

                    original_series = (
                        dataframe[column]
                    )

                    converted = pd.to_datetime(
                        original_series,
                        errors="coerce"
                    )

                    valid_count = int(
                        converted.notna().sum()
                    )

                    if valid_count > 0:

                        dataframe[column] = (
                            converted
                            .dt.strftime(
                                "%Y-%m-%d"
                            )
                        )

                        converted_columns.append(
                            str(column)
                        )

            if converted_columns:

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

            if selected_version:

                return redirect(
                    f"/data/transformation/"
                    f"?dataset={dataset.id}"
                    f"&version={selected_version.id}"
                )

            return redirect(
                f"/data/transformation/"
                f"?dataset={dataset.id}"
            )

        # ----------------------------------------------------
        # CREATE TRANSFORMED VERSION
        # ----------------------------------------------------

        # Deactivate previous current version
        DatasetVersion.objects.filter(
            dataset=dataset,
            is_current=True
        ).update(
            is_current=False
        )

        # ----------------------------------------------------
        # DETERMINE NEXT VERSION NUMBER
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

            next_version_number = (
                latest_version.version_number
                + 1
            )

        else:

            next_version_number = 1

        # ----------------------------------------------------
        # CREATE CSV CONTENT
        # ----------------------------------------------------

        csv_buffer = StringIO()

        dataframe.to_csv(
            csv_buffer,
            index=False
        )

        csv_content = (
            csv_buffer
            .getvalue()
            .encode("utf-8")
        )

        # ----------------------------------------------------
        # CALCULATE TRANSFORMED DATASET STATS
        # ----------------------------------------------------

        total_rows = len(dataframe)
        total_columns = len(dataframe.columns)

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

        total_cells = (
            total_rows
            *
            total_columns
        )

        completeness = (
            (
                (
                    total_cells
                    -
                    missing_values
                )
                /
                total_cells
            )
            *
            100
            if total_cells
            else 0
        )

        quality_score = round(
            completeness,
            2
        )

        # ----------------------------------------------------
        # CREATE VERSION
        # ----------------------------------------------------

        transformed_version = DatasetVersion(
            dataset=dataset,
            version_number=next_version_number,
            version_type="Transformed",
            is_current=True,

            row_count=total_rows,
            column_count=total_columns,
            missing_values=missing_values,
            duplicate_rows=duplicate_rows,
            quality_score=quality_score,
        )

        safe_name = (
            dataset.name
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
        )

        filename = (
            f"transformed_"
            f"{safe_name}_v"
            f"{next_version_number}.csv"
        )

        transformed_version.file.save(
            filename,
            ContentFile(
                csv_content
            ),
            save=False
        )

        transformed_version.save()

        # ----------------------------------------------------
        # DOWNLOAD TRANSFORMED DATASET
        # ----------------------------------------------------

        response = HttpResponse(
            csv_content,
            content_type="text/csv"
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{filename}"'
        )

        messages.success(
            request,
            (
                "Dataset transformed successfully. "
                f"Version {next_version_number} "
                "has been created."
            )
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
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    selected_dataset = None
    versions = []

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
    # VERSION HISTORY
    # --------------------------------------------------------

    if selected_dataset:

        versions = list(
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by(
                "-version_number"
            )
        )

        # ----------------------------------------------------
        # ATTACH EXTRA INFORMATION TO EACH VERSION
        # ----------------------------------------------------

        for version in versions:

            version.is_active_version = bool(
                version.is_current
            )

            version.version_label = (
                getattr(
                    version,
                    "version_type",
                    ""
                )
                or
                f"Version {version.version_number}"
            )

            version.version_badge = (
                version.version_label
                .lower()
                .replace(" ", "-")
            )

    # --------------------------------------------------------
    # CURRENT VERSION
    # --------------------------------------------------------

    current_version = None

    if selected_dataset:

        current_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                is_current=True
            )
            .order_by(
                "-version_number"
            )
            .first()
        )

    # --------------------------------------------------------
    # ORIGINAL VERSION
    # --------------------------------------------------------

    original_version = None

    if selected_dataset:

        original_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Original"
            )
            .order_by(
                "version_number"
            )
            .first()
        )

    # --------------------------------------------------------
    # CLEANED VERSION
    # --------------------------------------------------------

    cleaned_version = None

    if selected_dataset:

        cleaned_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Cleaned"
            )
            .order_by(
                "-version_number"
            )
            .first()
        )

    # --------------------------------------------------------
    # TRANSFORMED VERSION
    # --------------------------------------------------------

    transformed_version = None

    if selected_dataset:

        transformed_version = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset,
                version_type="Transformed"
            )
            .order_by(
                "-version_number"
            )
            .first()
        )

    # --------------------------------------------------------
    # DATASET VERSION SUMMARY
    # --------------------------------------------------------

    version_summary = {

        "total_versions":
            len(versions),

        "current_version":
            current_version,

        "original_version":
            original_version,

        "cleaned_version":
            cleaned_version,

        "transformed_version":
            transformed_version,
    }

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

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

            "current_version":
                current_version,

            "original_version":
                original_version,

            "cleaned_version":
                cleaned_version,

            "transformed_version":
                transformed_version,

            "version_summary":
                version_summary,
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
    # GET VERSION
    # --------------------------------------------------------

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
            "data_management:version_history"
        )

    # --------------------------------------------------------
    # CHECK FILE
    # --------------------------------------------------------

    try:

        if not version.file:

            messages.error(
                request,
                "This dataset version does not have a file."
            )

            return redirect(
                f"/data/version-history/"
                f"?dataset={version.dataset.id}"
            )

        # ----------------------------------------------------
        # DETERMINE FILE NAME
        # ----------------------------------------------------

        original_filename = (
            getattr(
                version,
                "file_name",
                ""
            )
            or
            ""
        )

        # If file_name is empty, use actual storage filename
        if not original_filename:

            try:

                original_filename = (
                    os.path.basename(
                        version.file.name
                    )
                )

            except Exception:

                original_filename = ""

        # ----------------------------------------------------
        # FILE EXTENSION
        # ----------------------------------------------------

        extension = os.path.splitext(
            original_filename
        )[1].lower()

        if extension == ".xlsx":

            content_type = (
                "application/"
                "vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )

        elif extension == ".xls":

            content_type = (
                "application/vnd.ms-excel"
            )

        elif extension == ".json":

            content_type = (
                "application/json"
            )

        else:

            extension = ".csv"

            content_type = (
                "text/csv"
            )

        # ----------------------------------------------------
        # OPEN FILE
        # ----------------------------------------------------

        file_handle = (
            version.file.open("rb")
        )

        response = HttpResponse(
            file_handle,
            content_type=content_type
        )

        # ----------------------------------------------------
        # SAFE DATASET NAME
        # ----------------------------------------------------

        safe_name = (
            str(
                version.dataset.name
            )
            .strip()
            .replace(" ", "_")
            .replace("/", "_")
            .replace("\\", "_")
            .replace(":", "_")
        )

        # ----------------------------------------------------
        # DOWNLOAD NAME
        # ----------------------------------------------------

        download_filename = (
            f"{safe_name}_"
            f"v{version.version_number}"
            f"{extension}"
        )

        response[
            "Content-Disposition"
        ] = (
            "attachment; "
            f'filename="{download_filename}"'
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
            f"/data/version-history/"
            f"?dataset={version.dataset.id}"
        )


# ============================================================
# DELETE / ARCHIVE DATASET
# ============================================================

@login_required
def delete_dataset(
    request,
    dataset_id
):

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
    # GET DATASET
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # ARCHIVE DATASET
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # CONFIRMATION PAGE
    # --------------------------------------------------------

    return render(
        request,
        "data_management/delete_dataset.html",
        {
            "dataset":
                dataset
        }
    )