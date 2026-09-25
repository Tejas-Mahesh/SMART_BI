from pathlib import Path

import pandas as pd

from data_management.models import DatasetVersion


SUPPORTED_EXTENSIONS = {
    ".csv",
    ".xls",
    ".xlsx",
}


def get_current_version(dataset):
    """
    Return the current DatasetVersion for a dataset.

    Falls back to the latest version if no version is explicitly
    marked as current.
    """

    if dataset is None:
        return None

    version = (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
            is_current=True,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )

    if version:
        return version

    return (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )


def get_dataset_versions(dataset):
    """
    Return all versions belonging to a dataset.
    """

    if dataset is None:
        return DatasetVersion.objects.none()

    return (
        DatasetVersion.objects
        .filter(
            dataset=dataset,
        )
        .order_by(
            "-version_number",
            "-created_at",
        )
    )


def validate_dataset_version(version):
    """
    Validate that the selected DatasetVersion has a usable file.
    """

    if version is None:
        raise ValueError(
            "No dataset version was selected."
        )

    if not version.file:
        raise ValueError(
            "The selected dataset version does not contain a file."
        )

    filename = (
        version.file_name
        or version.file.name
        or ""
    )

    extension = Path(filename).suffix.lower()

    if extension not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            "Unsupported dataset format. "
            "Supported formats are CSV, XLS, and XLSX."
        )

    return True


def read_dataset_version(version):
    """
    Read a DatasetVersion file into a pandas DataFrame.

    Reporting reads the exact DatasetVersion supplied to it.
    It does not modify the source file.
    """

    validate_dataset_version(version)

    filename = (
        version.file_name
        or version.file.name
        or ""
    )

    extension = Path(filename).suffix.lower()

    file_path = version.file.path

    if extension == ".csv":
        dataframe = pd.read_csv(
            file_path
        )

    elif extension in {".xls", ".xlsx"}:
        dataframe = pd.read_excel(
            file_path
        )

    else:
        raise ValueError(
            "Unsupported dataset format."
        )

    return dataframe


def get_dataset_metadata(version, dataframe=None):
    """
    Return basic metadata for the selected dataset version.
    """

    if version is None:
        return {
            "version_id": None,
            "version_number": None,
            "version_type": None,
            "file_name": "",
            "rows": 0,
            "columns": 0,
            "missing_values": 0,
            "duplicate_rows": 0,
        }

    if dataframe is None:
        dataframe = read_dataset_version(
            version
        )

    return {
        "version_id": version.id,
        "version_number": version.version_number,
        "version_type": version.version_type,
        "file_name": (
            version.file_name
            or version.file.name
            or ""
        ),
        "rows": int(
            len(dataframe)
        ),
        "columns": int(
            len(dataframe.columns)
        ),
        "missing_values": int(
            dataframe.isna().sum().sum()
        ),
        "duplicate_rows": int(
            dataframe.duplicated().sum()
        ),
    }


def prepare_dataframe(dataframe):
    """
    Prepare a dataframe for reporting calculations.

    This does not perform business-data cleaning.

    The Data Management module remains responsible for creating
    the cleaned DatasetVersion.

    Reporting only performs safe structural preparation.
    """

    if dataframe is None:
        raise ValueError(
            "No dataframe was provided."
        )

    dataframe = dataframe.copy()

    dataframe.columns = [
        str(column).strip()
        for column in dataframe.columns
    ]

    return dataframe


def load_reporting_dataset(dataset=None, version=None):
    """
    Load the exact DatasetVersion that Reporting should use.

    If a version is supplied, that exact version is used.

    If no version is supplied, the dataset's current version
    is selected automatically.

    Returns:
        {
            "dataset": dataset,
            "version": version,
            "dataframe": dataframe,
            "metadata": metadata,
        }
    """

    if dataset is None and version is None:
        raise ValueError(
            "A dataset or dataset version is required."
        )

    if version is None:
        version = get_current_version(
            dataset
        )

    if version is None:
        raise ValueError(
            "No dataset version is available."
        )

    if dataset is None:
        dataset = version.dataset

    if version.dataset_id != dataset.id:
        raise ValueError(
            "The selected dataset version does not "
            "belong to the selected dataset."
        )

    dataframe = read_dataset_version(
        version
    )

    dataframe = prepare_dataframe(
        dataframe
    )

    metadata = get_dataset_metadata(
        version,
        dataframe,
    )

    return {
        "dataset": dataset,
        "version": version,
        "dataframe": dataframe,
        "metadata": metadata,
    }