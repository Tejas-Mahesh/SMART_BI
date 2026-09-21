
# ============================================================
# DECISION INTELLIGENCE - VIEWS
# ============================================================

import pandas as pd

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import reverse

from data_management.models import Dataset, DatasetVersion

from .models import Recommendation
from .recommendation_engine import generate_recommendations


# ============================================================
# APPROVAL CHECK
# ============================================================

def user_is_approved(request):
    """
    Allows access only to administrator-approved users.
    """

    if not request.user.is_authenticated:
        return False

    return getattr(
        request.user,
        "approval_status",
        "",
    ) == "Approved"


# ============================================================
# DATASET READER
# ============================================================

def read_dataset_version_file(version):
    """
    Reads the selected DatasetVersion file.

    Supports:
        - CSV
        - XLSX
        - XLS
    """

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

    extension = (
        file_name
        .lower()
        .rsplit(".", 1)[-1]
        if "." in file_name
        else ""
    )

    version.file.open("rb")

    try:

        if extension == "csv":

            dataframe = pd.read_csv(
                version.file
            )

        elif extension in ["xlsx", "xls"]:

            dataframe = pd.read_excel(
                version.file
            )

        else:

            raise ValueError(
                "Unsupported dataset format. "
                "Only CSV, XLS and XLSX files are supported."
            )

    finally:

        version.file.close()

    if dataframe is None:

        raise ValueError(
            "Unable to read dataset version."
        )

    return dataframe


# ============================================================
# RECOMMENDATIONS
# ============================================================

@login_required
def recommendations(request):

    # --------------------------------------------------------
    # APPROVAL CHECK
    # --------------------------------------------------------

    if not user_is_approved(request):

        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been "
                    "approved by the administrator yet."
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

    selected_dataset = None
    selected_version = None

    versions = DatasetVersion.objects.none()

    # --------------------------------------------------------
    # SELECT DATASET
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    if dataset_id:

        selected_dataset = (
            datasets
            .filter(
                id=dataset_id,
            )
            .first()
        )

    if selected_dataset is None:

        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # AVAILABLE VERSIONS
    # --------------------------------------------------------

    if selected_dataset:

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

        version_id = request.GET.get(
            "version"
        )

        if version_id:

            selected_version = (
                versions
                .filter(
                    id=version_id,
                )
                .first()
            )

        # Prefer current version
        if selected_version is None:

            selected_version = (
                versions
                .filter(
                    is_current=True,
                )
                .first()
            )

        # Fallback to latest version
        if selected_version is None:

            selected_version = versions.first()

    # --------------------------------------------------------
    # LOAD SAVED RECOMMENDATIONS
    # --------------------------------------------------------

    recommendations_list = []

    if selected_dataset and selected_version:

        recommendations_list = list(
            Recommendation.objects
            .filter(
                dataset=selected_dataset,
                dataset_version=selected_version,
            )
            .order_by(
                "-created_at"
            )
        )

    # --------------------------------------------------------
    # RUN RECOMMENDATION ANALYSIS
    # --------------------------------------------------------

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "generate",
        )

        if action == "generate":

            post_dataset_id = request.POST.get(
                "dataset"
            )

            post_version_id = request.POST.get(
                "version"
            )

            # ------------------------------------------------
            # VALIDATE DATASET
            # ------------------------------------------------

            post_dataset = (
                datasets
                .filter(
                    id=post_dataset_id,
                )
                .first()
            )

            if not post_dataset:

                messages.error(
                    request,
                    "Please select a valid dataset.",
                )

                return redirect(
                    "decision_intelligence:recommendations"
                )

            # ------------------------------------------------
            # VALIDATE VERSION
            # ------------------------------------------------

            post_version = (
                DatasetVersion.objects
                .filter(
                    id=post_version_id,
                    dataset=post_dataset,
                )
                .first()
            )

            # Prefer current version if the
            # submitted version is invalid.
            if not post_version:

                post_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=post_dataset,
                        is_current=True,
                    )
                    .first()
                )

            # Fallback to latest version.
            if not post_version:

                post_version = (
                    DatasetVersion.objects
                    .filter(
                        dataset=post_dataset,
                    )
                    .order_by(
                        "-version_number",
                        "-created_at",
                    )
                    .first()
                )

            if not post_version:

                messages.error(
                    request,
                    "No dataset version is available.",
                )

                return redirect(
                    "decision_intelligence:recommendations"
                )

            # ------------------------------------------------
            # GENERATE RECOMMENDATIONS
            # ------------------------------------------------

            try:

                dataframe = read_dataset_version_file(
                    post_version
                )

                result = generate_recommendations(
                    dataframe
                )

                generated_recommendations = (
                    result.get(
                        "recommendations",
                        [],
                    )
                )

                summary = result.get(
                    "summary",
                    {},
                )

                # --------------------------------------------
                # SAVE RESULTS
                # --------------------------------------------

                with transaction.atomic():

                    # Remove only recommendations
                    # generated by this user for
                    # this exact dataset version.
                    Recommendation.objects.filter(
                        dataset=post_dataset,
                        dataset_version=post_version,
                        created_by=request.user,
                    ).delete()

                    for item in generated_recommendations:

                        Recommendation.objects.create(

                            dataset=post_dataset,

                            dataset_version=post_version,

                            created_by=request.user,

                            title=item.get(
                                "title",
                                "Business Recommendation",
                            ),

                            category=item.get(
                                "category",
                                "General",
                            ),

                            description=item.get(
                                "description",
                                "",
                            ),

                            supporting_insight=item.get(
                                "supporting_insight",
                                "",
                            ),

                            recommended_action=item.get(
                                "recommended_action",
                                "",
                            ),

                            expected_outcome=item.get(
                                "expected_outcome",
                                "",
                            ),

                            priority=item.get(
                                "priority",
                                "Medium",
                            ),

                            impact_level=item.get(
                                "impact_level",
                                "Medium",
                            ),

                            confidence=float(
                                item.get(
                                    "confidence",
                                    0,
                                )
                            ),

                            status="New",

                            metadata={
                                "engine": (
                                    "Recommendation Engine"
                                ),
                                "dataset_version": (
                                    post_version.version_number
                                ),
                                "generated_summary": summary,
                            },
                        )

                messages.success(
                    request,
                    (
                        f"{len(generated_recommendations)} "
                        "recommendation(s) generated successfully."
                    ),
                )

            except Exception as exc:

                messages.error(
                    request,
                    (
                        "Recommendation analysis failed: "
                        f"{str(exc)}"
                    ),
                )

            # ------------------------------------------------
            # CORRECT REDIRECT
            # ------------------------------------------------
            #
            # IMPORTANT:
            # Do not use:
            #
            # redirect(
            #     f"?dataset={post_dataset.id}"
            #     f"&version={post_version.id}"
            # )
            #
            # Django interprets that string as a URL name.
            #
            # Build the named URL first, then append
            # the query parameters.
            # ------------------------------------------------

            recommendations_url = reverse(
                "decision_intelligence:recommendations"
            )

            return redirect(
                f"{recommendations_url}"
                f"?dataset={post_dataset.id}"
                f"&version={post_version.id}"
            )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    total_recommendations = len(
        recommendations_list
    )

    high_priority_count = sum(
        1
        for recommendation in recommendations_list
        if recommendation.priority in [
            "High",
            "Critical",
        ]
    )

    high_impact_count = sum(
        1
        for recommendation in recommendations_list
        if recommendation.impact_level == "High"
    )

    average_confidence = 0

    if recommendations_list:

        average_confidence = round(
            sum(
                recommendation.confidence
                for recommendation
                in recommendations_list
            )
            / len(recommendations_list),
            2,
        )

    # --------------------------------------------------------
    # CATEGORY COUNTS
    # --------------------------------------------------------

    category_counts = {}

    for recommendation in recommendations_list:

        category = recommendation.category

        category_counts[category] = (
            category_counts.get(category, 0) + 1
        )

    # --------------------------------------------------------
    # PRIORITY COUNTS
    # --------------------------------------------------------

    priority_counts = {
        "Low": 0,
        "Medium": 0,
        "High": 0,
        "Critical": 0,
    }

    for recommendation in recommendations_list:

        if recommendation.priority in priority_counts:

            priority_counts[
                recommendation.priority
            ] += 1

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "datasets": datasets,

        "selected_dataset": selected_dataset,

        "versions": versions,

        "selected_version": selected_version,

        "recommendations": recommendations_list,

        "total_recommendations": (
            total_recommendations
        ),

        "high_priority_count": (
            high_priority_count
        ),

        "high_impact_count": (
            high_impact_count
        ),

        "average_confidence": (
            average_confidence
        ),

        "category_counts": category_counts,

        "priority_counts": priority_counts,

        "has_recommendations": (
            total_recommendations > 0
        ),
    }

    # --------------------------------------------------------
    # RENDER
    # --------------------------------------------------------

    return render(
        request,
        "decision_intelligence/recommendations.html",
        context,
    )
