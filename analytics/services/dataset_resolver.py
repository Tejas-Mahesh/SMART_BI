from dataclasses import dataclass

from data_management.models import Dataset, DatasetVersion
from data_management.views import read_dataset_version_file


@dataclass
class ResolvedDataset:
    dataset: Dataset
    version: DatasetVersion
    dataframe: object


DATASET_TYPES = {
    "sales": "Sales",
    "customer": "Customers",
    "customers": "Customers",
    "product": "Products",
    "products": "Products",
    "regional": "Regional",
    "marketing": "Marketing",
    "financial": "Financial",
    "returns": "Returns",
}


def normalize_dataset_type(dataset_type):
    """
    Convert an analytics dataset type name into the
    Dataset.dataset_type value used by Data Management.
    """

    if not dataset_type:
        return None

    return DATASET_TYPES.get(
        str(dataset_type).strip().lower()
    )


def get_user_datasets(user, dataset_type):
    """
    Return all active datasets of the requested type
    belonging to the current user.

    Datasets are returned newest first.
    """

    normalized_type = normalize_dataset_type(
        dataset_type
    )

    if not normalized_type:
        return Dataset.objects.none()

    return (
        Dataset.objects
        .filter(
            owner=user,
            dataset_type=normalized_type,
            is_active=True,
        )
        .order_by(
            "-uploaded_at",
            "-id",
        )
    )


def get_user_dataset(user, dataset_type, dataset_id=None):
    """
    Return a specific active dataset belonging to the
    current user.

    If dataset_id is not supplied, the newest active
    dataset of the requested type is returned.

    The dataset_id is always filtered through the
    current user's ownership, preventing users from
    accessing another user's dataset.
    """

    normalized_type = normalize_dataset_type(
        dataset_type
    )

    if not normalized_type:
        return None

    queryset = (
        Dataset.objects
        .filter(
            owner=user,
            dataset_type=normalized_type,
            is_active=True,
        )
    )

    if dataset_id:
        return (
            queryset
            .filter(id=dataset_id)
            .first()
        )

    return (
        queryset
        .order_by(
            "-uploaded_at",
            "-id",
        )
        .first()
    )


def get_current_dataset_version(dataset):
    """
    Resolve the version that Analytics should use.

    Priority:

    1. Current DatasetVersion
    2. Latest DatasetVersion

    This is important because a transformed version
    may have been marked as current by Data Management.
    """

    if dataset is None:
        return None

    current_version = (
        dataset.versions
        .filter(is_current=True)
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )

    if current_version:
        return current_version

    return (
        dataset.versions
        .order_by(
            "-version_number",
            "-created_at",
        )
        .first()
    )


def resolve_dataset(
    user,
    dataset_type,
    dataset_id=None,
):
    """
    Resolve a user's dataset and the version that
    Analytics should consume.

    If dataset_id is supplied, only that dataset is
    considered.

    If dataset_id is not supplied, the newest active
    dataset of the requested type is used.

    Returns:

        ResolvedDataset
        None

    Raises ValueError when a dataset/version exists
    but its file cannot be read.
    """

    dataset = get_user_dataset(
        user=user,
        dataset_type=dataset_type,
        dataset_id=dataset_id,
    )

    if dataset is None:
        return None

    version = get_current_dataset_version(
        dataset
    )

    if version is None:
        raise ValueError(
            f"No dataset version is available for "
            f"'{dataset.get_dataset_type_display()}'."
        )

    dataframe = read_dataset_version_file(
        version
    )

    if dataframe is None:
        raise ValueError(
            f"Unable to read the current version of "
            f"'{dataset.name}'."
        )

    return ResolvedDataset(
        dataset=dataset,
        version=version,
        dataframe=dataframe,
    )