
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


from .models import (
    Recommendation,
    WhatIfSimulation,
    ScenarioPlanning,
    BusinessAlert,
    ActionItem,
)

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


from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from data_management.models import Dataset, DatasetVersion
from data_management.views import (
    read_dataset_version_file,
    user_is_approved,
)

from .models import WhatIfSimulation
from .what_if_engine import run_what_if_simulation


# ============================================================
# WHAT-IF SIMULATOR
# ============================================================

@login_required
def what_if_simulator(request):

    # ========================================================
    # APPROVAL CHECK
    # ========================================================

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

    # ========================================================
    # AVAILABLE DATASETS
    # ========================================================

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

    # ========================================================
    # SELECT DATASET
    # ========================================================

    dataset_id = request.GET.get(
        "dataset"
    )

    if dataset_id:
        try:
            selected_dataset = (
                datasets
                .filter(id=dataset_id)
                .first()
            )
        except (
            TypeError,
            ValueError,
        ):
            selected_dataset = None

    # Fallback to latest uploaded dataset
    if selected_dataset is None:
        selected_dataset = datasets.first()

    # ========================================================
    # AVAILABLE VERSIONS
    # ========================================================

    if selected_dataset:

        versions = (
            DatasetVersion.objects
            .filter(
                dataset=selected_dataset
            )
            .order_by(
                "-version_number",
                "-created_at",
            )
        )

        version_id = request.GET.get(
            "version"
        )

        # ----------------------------------------------------
        # Requested version
        # ----------------------------------------------------

        if version_id:
            try:
                selected_version = (
                    versions
                    .filter(id=version_id)
                    .first()
                )
            except (
                TypeError,
                ValueError,
            ):
                selected_version = None

        # ----------------------------------------------------
        # Current version fallback
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
        # Latest version fallback
        # ----------------------------------------------------

        if selected_version is None:
            selected_version = versions.first()

    # ========================================================
    # DEFAULT ASSUMPTIONS
    # ========================================================

    assumptions = {
        "sales_change": 0,
        "profit_change": 0,
        "cost_change": 0,
        "quantity_change": 0,
        "customer_change": 0,
        "order_change": 0,
        "marketing_spend_change": 0,
        "returns_change": 0,
    }

    # ========================================================
    # CURRENT SIMULATION RESULT
    # ========================================================

    simulation_result = None

    # ========================================================
    # POST - RUN SIMULATION
    # ========================================================

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        if action == "simulate":

            # ------------------------------------------------
            # Validate posted dataset
            # ------------------------------------------------

            post_dataset_id = request.POST.get(
                "dataset"
            )

            try:
                post_dataset = (
                    datasets
                    .filter(
                        id=post_dataset_id
                    )
                    .first()
                )
            except (
                TypeError,
                ValueError,
            ):
                post_dataset = None

            if post_dataset is None:
                messages.error(
                    request,
                    "Please select a valid dataset.",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:"
                        "what_if_simulator"
                    )
                )

            # ------------------------------------------------
            # Validate posted version
            # ------------------------------------------------

            post_version_id = request.POST.get(
                "version"
            )

            post_versions = (
                DatasetVersion.objects
                .filter(
                    dataset=post_dataset
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
            )

            try:
                post_version = (
                    post_versions
                    .filter(
                        id=post_version_id
                    )
                    .first()
                )
            except (
                TypeError,
                ValueError,
            ):
                post_version = None

            if post_version is None:
                post_version = (
                    post_versions
                    .filter(
                        is_current=True
                    )
                    .first()
                )

            if post_version is None:
                post_version = post_versions.first()

            if post_version is None:
                messages.error(
                    request,
                    "The selected dataset has no available version.",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:"
                        "what_if_simulator"
                    )
                    + f"?dataset={post_dataset.id}"
                )

            # ------------------------------------------------
            # Read assumptions
            # ------------------------------------------------

            assumptions = {
                "sales_change": request.POST.get(
                    "sales_change",
                    0,
                ),
                "profit_change": request.POST.get(
                    "profit_change",
                    0,
                ),
                "cost_change": request.POST.get(
                    "cost_change",
                    0,
                ),
                "quantity_change": request.POST.get(
                    "quantity_change",
                    0,
                ),
                "customer_change": request.POST.get(
                    "customer_change",
                    0,
                ),
                "order_change": request.POST.get(
                    "order_change",
                    0,
                ),
                "marketing_spend_change": request.POST.get(
                    "marketing_spend_change",
                    0,
                ),
                "returns_change": request.POST.get(
                    "returns_change",
                    0,
                ),
            }

            # ------------------------------------------------
            # Simulation name
            # ------------------------------------------------

            simulation_name = (
                request.POST.get(
                    "simulation_name",
                    "",
                ).strip()
            )

            if not simulation_name:
                simulation_name = (
                    "What-If Simulation"
                )

            # ------------------------------------------------
            # Description
            # ------------------------------------------------

            simulation_description = (
                request.POST.get(
                    "simulation_description",
                    "",
                ).strip()
            )

            # ------------------------------------------------
            # Read selected cleaned/versioned dataset
            # ------------------------------------------------

            try:
                dataframe = read_dataset_version_file(
                    post_version
                )

                # ------------------------------------------------
                # Run simulation engine
                # ------------------------------------------------

                simulation_result = (
                    run_what_if_simulation(
                        dataframe,
                        assumptions,
                    )
                )

                # ------------------------------------------------
                # Save simulation
                # ------------------------------------------------

                WhatIfSimulation.objects.create(
                    dataset=post_dataset,
                    dataset_version=post_version,
                    created_by=request.user,
                    name=simulation_name,
                    description=simulation_description,
                    assumptions=simulation_result.get(
                        "assumptions",
                        {},
                    ),
                    baseline_results=simulation_result.get(
                        "baseline",
                        {},
                    ),
                    simulated_results=simulation_result.get(
                        "simulated",
                        {},
                    ),
                    result_summary=simulation_result.get(
                        "summary",
                        {},
                    ),
                    status="Completed",
                    error_message="",
                    completed_at=timezone.now(),
                )

                messages.success(
                    request,
                    "What-If simulation completed successfully.",
                )

                # ------------------------------------------------
                # PRG redirect
                # ------------------------------------------------

                return redirect(
                    f"{reverse('decision_intelligence:what_if_simulator')}"
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )

            except Exception as exc:

                messages.error(
                    request,
                    f"Simulation failed: {exc}",
                )

                simulation_result = None

                # Preserve selected dataset/version
                selected_dataset = post_dataset
                selected_version = post_version
                versions = post_versions

    # ========================================================
    # SAVED SIMULATIONS
    # ========================================================

    simulations = (
        WhatIfSimulation.objects
        .filter(
            dataset=selected_dataset,
            dataset_version=selected_version,
            created_by=request.user,
        )
        .order_by("-created_at")
        if selected_dataset
        and selected_version
        else WhatIfSimulation.objects.none()
    )

    latest_simulation = (
        simulations.first()
        if simulations.exists()
        else None
    )

    # ========================================================
    # IMPORTANT FIX
    #
    # After POST, the view redirects.
    # Therefore the next request is GET and the Python
    # variable simulation_result no longer exists.
    #
    # Reconstruct the exact structure expected by the template
    # from the saved simulation.
    # ========================================================

    if latest_simulation:

        simulation_result = {
            "baseline": (
                latest_simulation.baseline_results
                or {}
            ),
            "simulated": (
                latest_simulation.simulated_results
                or {}
            ),
            "summary": (
                latest_simulation.result_summary
                or {}
            ),
            "assumptions": (
                latest_simulation.assumptions
                or {}
            ),
        }

        # ----------------------------------------------------
        # Keep the selector values synchronized with the saved
        # simulation.
        # ----------------------------------------------------

        assumptions = {
            **assumptions,
            **(
                latest_simulation.assumptions
                or {}
            ),
        }

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "assumptions": assumptions,
        "simulation_result": simulation_result,
        "simulations": simulations,
        "latest_simulation": latest_simulation,
        "has_simulations": simulations.exists(),
    }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "decision_intelligence/what_if_simulator.html",
        context,
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    Recommendation,
    WhatIfSimulation,
    ScenarioPlanning,
)
# ============================================================
# SCENARIO PLANNING
# ============================================================

@login_required
def scenario_planning(request):
    """
    Scenario Planning

    Uses the selected cleaned DatasetVersion as the source of
    the scenario calculation.
    """

    if not user_is_approved(request):
        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            },
        )

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
            .filter(id=dataset_id)
            .first()
        )

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # SELECT DATASET VERSION
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

        version_id = request.GET.get("version")

        if version_id:
            selected_version = (
                versions
                .filter(id=version_id)
                .first()
            )

        if selected_version is None:
            selected_version = (
                versions
                .filter(is_current=True)
                .first()
            )

        if selected_version is None:
            selected_version = versions.first()

    # --------------------------------------------------------
    # DEFAULT ASSUMPTIONS
    # --------------------------------------------------------

    assumptions = {
        "sales_change": 0,
        "profit_change": 0,
        "cost_change": 0,
        "quantity_change": 0,
        "customer_change": 0,
        "order_change": 0,
        "marketing_spend_change": 0,
        "returns_change": 0,
    }

    scenario_result = None

    # --------------------------------------------------------
    # POST - RUN SCENARIO
    # --------------------------------------------------------

    if request.method == "POST":

        action = request.POST.get(
            "action",
            "",
        )

        if action == "run_scenario":

            post_dataset_id = request.POST.get(
                "dataset"
            )

            post_version_id = request.POST.get(
                "version"
            )

            post_dataset = (
                datasets
                .filter(
                    id=post_dataset_id,
                )
                .first()
            )

            if post_dataset is None:
                messages.error(
                    request,
                    "Please select a valid dataset.",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:scenario_planning"
                    )
                )

            post_versions = (
                DatasetVersion.objects
                .filter(
                    dataset=post_dataset,
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
            )

            post_version = (
                post_versions
                .filter(
                    id=post_version_id,
                )
                .first()
            )

            if post_version is None:
                messages.error(
                    request,
                    "Please select a valid dataset version.",
                )

                return redirect(
                    f"{reverse('decision_intelligence:scenario_planning')}"
                    f"?dataset={post_dataset.id}"
                )

            # ------------------------------------------------
            # READ SCENARIO INPUTS
            # ------------------------------------------------

            assumptions = {
                "sales_change": request.POST.get(
                    "sales_change",
                    0,
                ),
                "profit_change": request.POST.get(
                    "profit_change",
                    0,
                ),
                "cost_change": request.POST.get(
                    "cost_change",
                    0,
                ),
                "quantity_change": request.POST.get(
                    "quantity_change",
                    0,
                ),
                "customer_change": request.POST.get(
                    "customer_change",
                    0,
                ),
                "order_change": request.POST.get(
                    "order_change",
                    0,
                ),
                "marketing_spend_change": request.POST.get(
                    "marketing_spend_change",
                    0,
                ),
                "returns_change": request.POST.get(
                    "returns_change",
                    0,
                ),
            }

            scenario_name = (
                request.POST.get(
                    "name",
                    "",
                ).strip()
                or "Business Scenario"
            )

            scenario_description = (
                request.POST.get(
                    "description",
                    "",
                ).strip()
            )

            scenario_type = (
                request.POST.get(
                    "scenario_type",
                    "Custom",
                ).strip()
                or "Custom"
            )

            try:

                # --------------------------------------------
                # IMPORT ENGINE
                # --------------------------------------------

                from .scenario_engine import (
                    run_scenario,
                )

                # --------------------------------------------
                # READ CLEANED/VERSIONED DATA
                # --------------------------------------------

                dataframe = read_dataset_version_file(
                    post_version
                )

                # --------------------------------------------
                # RUN SCENARIO
                # --------------------------------------------

                scenario_result = run_scenario(
                    dataframe,
                    assumptions,
                )

                # --------------------------------------------
                # SAVE SCENARIO
                # --------------------------------------------

                ScenarioPlanning.objects.create(
                    dataset=post_dataset,
                    dataset_version=post_version,
                    created_by=request.user,
                    name=scenario_name,
                    description=scenario_description,
                    scenario_type=scenario_type,
                    assumptions=scenario_result.get(
                        "assumptions",
                        {},
                    ),
                    baseline_results=scenario_result.get(
                        "baseline",
                        {},
                    ),
                    projected_results=scenario_result.get(
                        "projected",
                        {},
                    ),
                    comparison_results=scenario_result.get(
                        "comparison",
                        {},
                    ),
                    status="Completed",
                    error_message="",
                    completed_at=timezone.now(),
                )

                messages.success(
                    request,
                    "Scenario planning completed successfully.",
                )

                # --------------------------------------------
                # PRG REDIRECT
                # --------------------------------------------

                return redirect(
                    f"{reverse('decision_intelligence:scenario_planning')}"
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )

            except Exception as exc:

                ScenarioPlanning.objects.create(
                    dataset=post_dataset,
                    dataset_version=post_version,
                    created_by=request.user,
                    name=scenario_name,
                    description=scenario_description,
                    scenario_type=scenario_type,
                    assumptions=assumptions,
                    status="Failed",
                    error_message=str(exc),
                )

                messages.error(
                    request,
                    f"Scenario planning failed: {exc}",
                )

                return redirect(
                    f"{reverse('decision_intelligence:scenario_planning')}"
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )

    # --------------------------------------------------------
    # LOAD SAVED SCENARIOS
    # --------------------------------------------------------

    scenarios = (
        ScenarioPlanning.objects
        .filter(
            dataset=selected_dataset,
            dataset_version=selected_version,
            created_by=request.user,
        )
        .order_by("-created_at")
        if selected_dataset and selected_version
        else ScenarioPlanning.objects.none()
    )

    # --------------------------------------------------------
    # LATEST COMPLETED SCENARIO
    # --------------------------------------------------------

    latest_scenario = (
        scenarios
        .filter(
            status="Completed",
        )
        .first()
        if scenarios.exists()
        else None
    )

    # --------------------------------------------------------
    # RECONSTRUCT RESULT AFTER REDIRECT
    # --------------------------------------------------------

    if latest_scenario:

        scenario_result = {
            "baseline": (
                latest_scenario.baseline_results
                or {}
            ),
            "projected": (
                latest_scenario.projected_results
                or {}
            ),
            "comparison": (
                latest_scenario.comparison_results
                or {}
            ),
            "summary": {
                "sales_change": (
                    latest_scenario
                    .comparison_results
                    .get("sales", {})
                    .get(
                        "percentage_change",
                        0,
                    )
                ),
                "profit_change": (
                    latest_scenario
                    .comparison_results
                    .get("profit", {})
                    .get(
                        "percentage_change",
                        0,
                    )
                ),
                "cost_change": (
                    latest_scenario
                    .comparison_results
                    .get("cost", {})
                    .get(
                        "percentage_change",
                        0,
                    )
                ),
            },
            "assumptions": (
                latest_scenario.assumptions
                or {}
            ),
        }

        # Use the latest saved assumptions in the form.
        assumptions = (
            latest_scenario.assumptions
            or assumptions
        )

    # --------------------------------------------------------
    # DISPLAY METRICS
    # --------------------------------------------------------

    display_metrics = []

    if scenario_result:

        comparison = scenario_result.get(
            "comparison",
            {},
        )

        metric_definitions = [
            (
                "Sales",
                "sales",
            ),
            (
                "Profit",
                "profit",
            ),
            (
                "Cost",
                "cost",
            ),
            (
                "Quantity",
                "quantity",
            ),
            (
                "Customers",
                "customers",
            ),
            (
                "Orders",
                "orders",
            ),
            (
                "Marketing Spend",
                "marketing_spend",
            ),
            (
                "Returns",
                "returns",
            ),
            (
                "Average Order Value",
                "average_order_value",
            ),
            (
                "Profit Margin",
                "profit_margin",
            ),
            (
                "Return Rate",
                "return_rate",
            ),
        ]

        for label, key in metric_definitions:

            result = comparison.get(
                key,
                {},
            )

            display_metrics.append(
                {
                    "label": label,
                    "key": key,
                    "baseline": result.get(
                        "baseline",
                        0,
                    ),
                    "projected": result.get(
                        "projected",
                        0,
                    ),
                    "absolute_change": result.get(
                        "absolute_change",
                        0,
                    ),
                    "percentage_change": result.get(
                        "percentage_change",
                        0,
                    ),
                }
            )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,

        "assumptions": assumptions,

        "scenario_result": scenario_result,

        "scenarios": scenarios,
        "latest_scenario": latest_scenario,

        "display_metrics": display_metrics,

        "has_scenarios": scenarios.exists(),
    }

    return render(
        request,
        "decision_intelligence/scenario_planning.html",
        context,
    )
from .models import (
    Recommendation,
    WhatIfSimulation,
    ScenarioPlanning,
    BusinessAlert,
)
# ============================================================
# BUSINESS ALERTS
# ============================================================

@login_required
def business_alerts(request):
    """
    Business Alerts dashboard.

    Alerts are generated from the selected cleaned/versioned
    dataset and stored against the exact DatasetVersion used
    for detection.
    """

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
            },
        )

    # --------------------------------------------------------
    # USER DATASETS
    # --------------------------------------------------------

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True,
    ).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None
    versions = DatasetVersion.objects.none()

    # --------------------------------------------------------
    # SELECT DATASET
    # --------------------------------------------------------

    dataset_id = request.GET.get("dataset")

    if dataset_id:
        try:
            selected_dataset = datasets.get(
                id=dataset_id
            )
        except Dataset.DoesNotExist:
            selected_dataset = None

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # DATASET VERSIONS
    # --------------------------------------------------------

    if selected_dataset:
        versions = selected_dataset.versions.all().order_by(
            "-version_number",
            "-created_at",
        )

        version_id = request.GET.get("version")

        if version_id:
            try:
                selected_version = versions.get(
                    id=version_id
                )
            except DatasetVersion.DoesNotExist:
                selected_version = None

        if selected_version is None:
            selected_version = versions.filter(
                is_current=True
            ).first()

        if selected_version is None:
            selected_version = versions.first()

    # --------------------------------------------------------
    # POST — GENERATE BUSINESS ALERTS
    # --------------------------------------------------------

    if request.method == "POST":

        action = request.POST.get("action")

        if action == "generate":

            post_dataset_id = request.POST.get(
                "dataset_id"
            )

            post_version_id = request.POST.get(
                "version_id"
            )

            # --------------------------------------------
            # VALIDATE DATASET
            # --------------------------------------------

            try:
                post_dataset = datasets.get(
                    id=post_dataset_id
                )
            except (
                Dataset.DoesNotExist,
                TypeError,
                ValueError,
            ):
                messages.error(
                    request,
                    "The selected dataset could not be found.",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:business_alerts"
                    )
                )

            # --------------------------------------------
            # VALIDATE VERSION
            # --------------------------------------------

            try:
                post_version = (
                    DatasetVersion.objects.get(
                        id=post_version_id,
                        dataset=post_dataset,
                    )
                )
            except (
                DatasetVersion.DoesNotExist,
                TypeError,
                ValueError,
            ):
                messages.error(
                    request,
                    "The selected dataset version could not be found.",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:business_alerts"
                    )
                    + f"?dataset={post_dataset.id}"
                )

            # --------------------------------------------
            # READ SELECTED VERSION
            # --------------------------------------------

            try:
                dataframe = read_dataset_version_file(
                    post_version
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"Unable to read the selected dataset version: {exc}",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:business_alerts"
                    )
                    + (
                        f"?dataset={post_dataset.id}"
                        f"&version={post_version.id}"
                    )
                )

            # --------------------------------------------
            # RUN ALERT ENGINE
            # --------------------------------------------

            try:
                from .business_alert_engine import (
                    generate_business_alerts,
                )

                alert_result = (
                    generate_business_alerts(
                        dataframe
                    )
                )

                generated_alerts = (
                    alert_result.get(
                        "alerts",
                        [],
                    )
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"Business alert detection failed: {exc}",
                )

                return redirect(
                    reverse(
                        "decision_intelligence:business_alerts"
                    )
                    + (
                        f"?dataset={post_dataset.id}"
                        f"&version={post_version.id}"
                    )
                )

            # --------------------------------------------
            # REMOVE PREVIOUS ALERTS
            # FOR SAME DATASET + VERSION + USER
            # --------------------------------------------

            BusinessAlert.objects.filter(
                dataset=post_dataset,
                dataset_version=post_version,
                created_by=request.user,
                status__in=[
                    "New",
                    "Acknowledged",
                ],
            ).delete()

            # --------------------------------------------
            # SAVE NEW ALERTS
            # --------------------------------------------

            created_count = 0

            for alert in generated_alerts:

                BusinessAlert.objects.create(
                    dataset=post_dataset,
                    dataset_version=post_version,
                    created_by=request.user,
                    title=alert.get(
                        "title",
                        "Business Alert",
                    ),
                    category=alert.get(
                        "category",
                        "General",
                    ),
                    severity=alert.get(
                        "severity",
                        "Medium",
                    ),
                    description=alert.get(
                        "description",
                        "",
                    ),
                    trigger_type=alert.get(
                        "trigger_type",
                        "Threshold",
                    ),
                    metric_name=alert.get(
                        "metric_name",
                        "",
                    ),
                    metric_value=alert.get(
                        "metric_value",
                        0,
                    ),
                    threshold_value=alert.get(
                        "threshold_value",
                        0,
                    ),
                    comparison_operator=alert.get(
                        "comparison_operator",
                        ">",
                    ),
                    recommended_action=alert.get(
                        "recommended_action",
                        "",
                    ),
                    metadata=alert.get(
                        "metadata",
                        {},
                    ),
                    status="New",
                )

                created_count += 1

            # --------------------------------------------
            # SUCCESS MESSAGE
            # --------------------------------------------

            if created_count:
                messages.success(
                    request,
                    (
                        f"{created_count} business alert"
                        f"{'s' if created_count != 1 else ''} "
                        "detected successfully."
                    ),
                )
            else:
                messages.success(
                    request,
                    "No business alerts were detected for the selected dataset.",
                )

            # --------------------------------------------
            # REDIRECT
            # --------------------------------------------

            return redirect(
                reverse(
                    "decision_intelligence:business_alerts"
                )
                + (
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )
            )

    # --------------------------------------------------------
    # LOAD SAVED ALERTS
    # --------------------------------------------------------

    alerts = BusinessAlert.objects.none()

    if selected_dataset and selected_version:

        alerts = BusinessAlert.objects.filter(
            dataset=selected_dataset,
            dataset_version=selected_version,
            created_by=request.user,
        ).order_by(
            "-detected_at"
        )

    # --------------------------------------------------------
    # ALERT SUMMARY
    # --------------------------------------------------------

    alert_summary = {
        "total": alerts.count(),
        "new": alerts.filter(
            status="New"
        ).count(),
        "acknowledged": alerts.filter(
            status="Acknowledged"
        ).count(),
        "resolved": alerts.filter(
            status="Resolved"
        ).count(),
        "critical": alerts.filter(
            severity="Critical"
        ).count(),
        "high": alerts.filter(
            severity="High"
        ).count(),
        "medium": alerts.filter(
            severity="Medium"
        ).count(),
        "low": alerts.filter(
            severity="Low"
        ).count(),
        "info": alerts.filter(
            severity="Info"
        ).count(),
    }

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "alerts": alerts,
        "alert_summary": alert_summary,
        "has_alerts": alerts.exists(),
    }

    return render(
        request,
        "decision_intelligence/business_alerts.html",
        context,
    )


@login_required
def action_center(request):
    if not user_is_approved(request):
        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved by the "
                    "administrator yet."
                )
            },
        )

    datasets = Dataset.objects.filter(
        owner=request.user,
        is_active=True,
    ).order_by("-uploaded_at")

    selected_dataset = None
    selected_version = None
    versions = DatasetVersion.objects.none()

    dataset_id = request.GET.get("dataset")
    version_id = request.GET.get("version")

    if dataset_id:
        selected_dataset = datasets.filter(
            id=dataset_id
        ).first()

    if selected_dataset is None:
        selected_dataset = datasets.first()

    if selected_dataset:
        versions = DatasetVersion.objects.filter(
            dataset=selected_dataset
        ).order_by("-version_number", "-created_at")

        if version_id:
            selected_version = versions.filter(
                id=version_id
            ).first()

        if selected_version is None:
            selected_version = versions.filter(
                is_current=True
            ).first()

        if selected_version is None:
            selected_version = versions.first()

    action_items = ActionItem.objects.none()

    if selected_dataset and selected_version:
        action_items = (
            ActionItem.objects
            .filter(
                dataset=selected_dataset,
                dataset_version=selected_version,
                created_by=request.user,
            )
            .select_related(
                "recommendation",
                "alert",
                "assigned_to",
            )
            .order_by("-created_at")
        )

    if request.method == "POST":
        action = request.POST.get("action", "").strip()

        if action == "create":
            post_dataset_id = request.POST.get("dataset")
            post_version_id = request.POST.get("version")

            post_dataset = datasets.filter(
                id=post_dataset_id
            ).first()

            if post_dataset is None:
                messages.error(
                    request,
                    "The selected dataset is not available.",
                )
                return redirect(
                    "decision_intelligence:action_center"
                )

            post_version = DatasetVersion.objects.filter(
                id=post_version_id,
                dataset=post_dataset,
            ).first()

            if post_version is None:
                messages.error(
                    request,
                    "The selected dataset version is not available.",
                )
                return redirect(
                    "decision_intelligence:action_center",
                )

            title = request.POST.get("title", "").strip()
            description = request.POST.get(
                "description",
                "",
            ).strip()
            action_text = request.POST.get(
                "action_text",
                "",
            ).strip()
            expected_outcome = request.POST.get(
                "expected_outcome",
                "",
            ).strip()

            category = request.POST.get(
                "category",
                "General",
            )

            priority = request.POST.get(
                "priority",
                "Medium",
            )

            due_date = request.POST.get(
                "due_date",
                "",
            ).strip()

            if not title:
                messages.error(
                    request,
                    "Please enter an action title.",
                )
                return redirect(
                    f"{reverse('decision_intelligence:action_center')}"
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )

            if not action_text:
                messages.error(
                    request,
                    "Please describe the action that should be performed.",
                )
                return redirect(
                    f"{reverse('decision_intelligence:action_center')}"
                    f"?dataset={post_dataset.id}"
                    f"&version={post_version.id}"
                )

            valid_categories = {
                choice[0]
                for choice in ActionItem.CATEGORY_CHOICES
            }

            valid_priorities = {
                choice[0]
                for choice in ActionItem.PRIORITY_CHOICES
            }

            if category not in valid_categories:
                category = "General"

            if priority not in valid_priorities:
                priority = "Medium"

            ActionItem.objects.create(
                dataset=post_dataset,
                dataset_version=post_version,
                created_by=request.user,
                title=title,
                description=description,
                action=action_text,
                expected_outcome=expected_outcome,
                category=category,
                source_type="Manual",
                priority=priority,
                status="New",
                due_date=due_date or None,
            )

            messages.success(
                request,
                "Action item created successfully.",
            )

            return redirect(
                f"{reverse('decision_intelligence:action_center')}"
                f"?dataset={post_dataset.id}"
                f"&version={post_version.id}"
            )

        if action == "update_status":
            action_item_id = request.POST.get(
                "action_item_id"
            )

            new_status = request.POST.get(
                "status",
                "",
            ).strip()

            valid_statuses = {
                choice[0]
                for choice in ActionItem.STATUS_CHOICES
            }

            if new_status not in valid_statuses:
                messages.error(
                    request,
                    "Invalid action status.",
                )
                return redirect(
                    request.get_full_path()
                )

            action_item = (
                ActionItem.objects
                .filter(
                    id=action_item_id,
                    created_by=request.user,
                )
                .first()
            )

            if action_item is None:
                messages.error(
                    request,
                    "Action item not found.",
                )
                return redirect(
                    request.get_full_path()
                )

            action_item.status = new_status

            if new_status == "Completed":
                action_item.completed_at = timezone.now()
            else:
                action_item.completed_at = None

            action_item.save(
                update_fields=[
                    "status",
                    "completed_at",
                    "updated_at",
                ]
            )

            messages.success(
                request,
                "Action status updated successfully.",
            )

            return redirect(
                request.get_full_path()
            )

    total_actions = action_items.count()

    status_summary = {
        "new": action_items.filter(
            status="New"
        ).count(),
        "planned": action_items.filter(
            status="Planned"
        ).count(),
        "in_progress": action_items.filter(
            status="In Progress"
        ).count(),
        "completed": action_items.filter(
            status="Completed"
        ).count(),
        "cancelled": action_items.filter(
            status="Cancelled"
        ).count(),
    }

    priority_summary = {
        "critical": action_items.filter(
            priority="Critical"
        ).count(),
        "high": action_items.filter(
            priority="High"
        ).count(),
        "medium": action_items.filter(
            priority="Medium"
        ).count(),
        "low": action_items.filter(
            priority="Low"
        ).count(),
    }

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,
        "action_items": action_items,
        "total_actions": total_actions,
        "status_summary": status_summary,
        "priority_summary": priority_summary,
        "category_choices": ActionItem.CATEGORY_CHOICES,
        "priority_choices": ActionItem.PRIORITY_CHOICES,
        "status_choices": ActionItem.STATUS_CHOICES,
    }

    return render(
        request,
        "decision_intelligence/action_center.html",
        context,
    )

# ============================================================
# DECISION IMPACT ANALYSIS
# ============================================================

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from data_management.models import Dataset, DatasetVersion

from .decision_impact_engine import generate_decision_impact_analysis
from .models import (
    Recommendation,
    WhatIfSimulation,
    ScenarioPlanning,
    BusinessAlert,
    ActionItem,
    DecisionImpactAnalysis,
)


# ============================================================
# DECISION IMPACT ANALYSIS VIEW
# ============================================================

@login_required
def decision_impact_analysis(request):
    """
    Decision Impact Analysis.

    Uses the selected cleaned/current DatasetVersion and
    compares an entered baseline and expected change against
    the actual metric calculated from that version.
    """

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

    # --------------------------------------------------------
    # SELECT DATASET
    # --------------------------------------------------------

    selected_dataset_id = request.GET.get("dataset")

    selected_dataset = None

    if selected_dataset_id:
        selected_dataset = (
            datasets
            .filter(id=selected_dataset_id)
            .first()
        )

    if selected_dataset is None:
        selected_dataset = datasets.first()

    # --------------------------------------------------------
    # AVAILABLE VERSIONS
    # --------------------------------------------------------

    versions = DatasetVersion.objects.none()
    selected_version = None

    if selected_dataset:
        versions = (
            selected_dataset.versions
            .all()
            .order_by("-version_number", "-created_at")
        )

        selected_version_id = request.GET.get("version")

        if selected_version_id:
            selected_version = (
                versions
                .filter(id=selected_version_id)
                .first()
            )

        if selected_version is None:
            selected_version = (
                versions
                .filter(is_current=True)
                .first()
            )

        if selected_version is None:
            selected_version = versions.first()

    # --------------------------------------------------------
    # AVAILABLE METRICS
    # --------------------------------------------------------

    available_metrics = [
        {
            "value": "sales",
            "label": "Sales / Revenue",
        },
        {
            "value": "profit",
            "label": "Profit",
        },
        {
            "value": "cost",
            "label": "Cost / Expenses",
        },
        {
            "value": "quantity",
            "label": "Quantity / Units",
        },
        {
            "value": "customers",
            "label": "Customers",
        },
        {
            "value": "orders",
            "label": "Orders",
        },
        {
            "value": "marketing_spend",
            "label": "Marketing Spend",
        },
        {
            "value": "returns",
            "label": "Returns",
        },
        {
            "value": "average_order_value",
            "label": "Average Order Value",
        },
        {
            "value": "profit_margin",
            "label": "Profit Margin",
        },
        {
            "value": "return_rate",
            "label": "Return Rate",
        },
    ]

    # --------------------------------------------------------
    # FORM SUBMISSION
    # --------------------------------------------------------

    if request.method == "POST":

        action = request.POST.get("action", "").strip()

        if action == "analyze":

            if not selected_dataset:
                messages.error(
                    request,
                    "Please select a dataset before running "
                    "Decision Impact Analysis.",
                )

                return redirect(
                    "decision_intelligence:decision_impact_analysis"
                )

            if not selected_version:
                messages.error(
                    request,
                    "The selected dataset does not have an "
                    "available version.",
                )

                return redirect(
                    "decision_intelligence:decision_impact_analysis"
                )

            metric_name = request.POST.get(
                "metric_name",
                "",
            ).strip()

            title = request.POST.get(
                "title",
                "",
            ).strip()

            description = request.POST.get(
                "description",
                "",
            ).strip()

            category = request.POST.get(
                "category",
                "General",
            ).strip()

            baseline_raw = request.POST.get(
                "baseline_value",
                "",
            ).strip()

            expected_change_raw = request.POST.get(
                "expected_change",
                "",
            ).strip()

            # ------------------------------------------------
            # VALIDATE REQUIRED INPUTS
            # ------------------------------------------------

            if not metric_name:
                messages.error(
                    request,
                    "Please select a metric.",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            if not baseline_raw:
                messages.error(
                    request,
                    "Please enter the baseline value.",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            if not expected_change_raw:
                messages.error(
                    request,
                    "Please enter the expected percentage change.",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            try:
                baseline_value = float(
                    baseline_raw.replace(",", "")
                )
            except (TypeError, ValueError):
                messages.error(
                    request,
                    "Baseline value must be a valid number.",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            try:
                expected_change = float(
                    expected_change_raw.replace(",", "")
                )
            except (TypeError, ValueError):
                messages.error(
                    request,
                    "Expected change must be a valid percentage.",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            if not title:
                title = "Decision Impact Analysis"

            # ------------------------------------------------
            # READ CLEANED/VERSIONED DATA
            # ------------------------------------------------

            try:
                from data_management.views import (
                    read_dataset_version_file,
                )

                dataframe = read_dataset_version_file(
                    selected_version
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"Unable to read the selected dataset version: {exc}",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            # ------------------------------------------------
            # RUN ENGINE
            # ------------------------------------------------

            try:
                result = generate_decision_impact_analysis(
                    dataframe=dataframe,
                    metric_name=metric_name,
                    baseline_value=baseline_value,
                    expected_change=expected_change,
                    title=title,
                    category=category,
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"Decision Impact Analysis failed: {exc}",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            # ------------------------------------------------
            # SAVE ANALYSIS
            # ------------------------------------------------

            try:
                analysis = DecisionImpactAnalysis.objects.create(
                    dataset=selected_dataset,
                    dataset_version=selected_version,
                    created_by=request.user,
                    title=result["title"],
                    description=description,
                    category=result["category"],
                    metric_name=result["metric_name"],
                    baseline_value=result["baseline_value"],
                    expected_value=result["expected_value"],
                    actual_value=result["actual_value"],
                    expected_change=result["expected_change"],
                    actual_change=result["actual_change"],
                    impact_value=result["impact_value"],
                    impact_percentage=result["impact_percentage"],
                    impact_type=result["impact_type"],
                    status=result.get(
                        "status",
                        "Monitoring",
                    ),
                    analysis_notes=result.get(
                        "analysis_notes",
                        "",
                    ),
                    metadata=result.get(
                        "metadata",
                        {},
                    ),
                    analyzed_at=timezone.now(),
                )

            except Exception as exc:
                messages.error(
                    request,
                    f"Unable to save the impact analysis: {exc}",
                )

                return redirect(
                    f"{request.path}"
                    f"?dataset={selected_dataset.id}"
                    f"&version={selected_version.id}"
                )

            messages.success(
                request,
                "Decision Impact Analysis completed successfully.",
            )

            return redirect(
                f"{request.path}"
                f"?dataset={selected_dataset.id}"
                f"&version={selected_version.id}"
                f"&analysis={analysis.id}"
            )

    # --------------------------------------------------------
    # LOAD PREVIOUS ANALYSES
    # --------------------------------------------------------

    analyses = DecisionImpactAnalysis.objects.none()

    if selected_dataset and selected_version:

        analyses = (
            DecisionImpactAnalysis.objects
            .filter(
                dataset=selected_dataset,
                dataset_version=selected_version,
                created_by=request.user,
            )
            .order_by("-created_at")
        )

    # --------------------------------------------------------
    # SELECTED ANALYSIS
    # --------------------------------------------------------

    selected_analysis = None

    analysis_id = request.GET.get("analysis")

    if analysis_id and selected_dataset and selected_version:

        selected_analysis = (
            analyses
            .filter(id=analysis_id)
            .first()
        )

    if selected_analysis is None:
        selected_analysis = analyses.first()

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = {
        "total": analyses.count(),
        "monitoring": analyses.filter(
            status="Monitoring"
        ).count(),
        "completed": analyses.filter(
            status="Completed"
        ).count(),
        "positive": analyses.filter(
            impact_type="Positive"
        ).count(),
        "neutral": analyses.filter(
            impact_type="Neutral"
        ).count(),
        "negative": analyses.filter(
            impact_type="Negative"
        ).count(),
    }

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "datasets": datasets,
        "selected_dataset": selected_dataset,
        "versions": versions,
        "selected_version": selected_version,

        "available_metrics": available_metrics,

        "analyses": analyses,
        "selected_analysis": selected_analysis,

        "summary": summary,
    }

    return render(
        request,
        "decision_intelligence/decision_impact_analysis.html",
        context,
    )
