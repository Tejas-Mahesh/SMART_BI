from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from data_management.models import (
    Dataset,
    DatasetVersion,
)


User = get_user_model()


# ============================================================
# ADMIN ACCESS
# ============================================================

def admin_required(view_function):

    @wraps(view_function)
    @login_required
    def wrapper(request, *args, **kwargs):

        if not (
            request.user.is_staff
            or request.user.is_superuser
        ):
            messages.error(
                request,
                "You do not have permission to access the Admin Dashboard."
            )

            return redirect("core:dashboard")

        return view_function(
            request,
            *args,
            **kwargs
        )

    return wrapper


# ============================================================
# COMMON USER QUERY
# ============================================================

def normal_user_queryset():

    return User.objects.filter(
        is_staff=False,
        is_superuser=False
    )


# ============================================================
# ADMIN DASHBOARD
# ============================================================

@admin_required
def dashboard(request):

    normal_users = normal_user_queryset()

    # --------------------------------------------------------
    # USER COUNTS
    # --------------------------------------------------------

    total_users = normal_users.count()

    pending_users = normal_users.filter(
        approval_status="Pending"
    ).count()

    approved_users = normal_users.filter(
        approval_status="Approved"
    ).count()

    rejected_users = normal_users.filter(
        approval_status="Rejected"
    ).count()

    active_users = normal_users.filter(
        is_active=True
    ).count()

    inactive_users = normal_users.filter(
        is_active=False
    ).count()

    # --------------------------------------------------------
    # DATASET COUNTS
    # --------------------------------------------------------

    active_datasets = Dataset.objects.filter(
        is_active=True
    )

    total_datasets = active_datasets.count()

    # --------------------------------------------------------
    # DATASET TYPE COUNTS
    # --------------------------------------------------------

    dataset_type_counts = (
        active_datasets
        .values("dataset_type")
        .annotate(total=Count("id"))
        .order_by("dataset_type")
    )

    # --------------------------------------------------------
    # RECENT USERS
    # --------------------------------------------------------

    recent_users = (
        normal_users
        .annotate(
            dataset_count=Count(
                "datasets",
                filter=Q(
                    datasets__is_active=True
                ),
                distinct=True
            )
        )
        .order_by("-date_joined")[:8]
    )

    # --------------------------------------------------------
    # PENDING USERS
    # --------------------------------------------------------

    pending_user_list = (
        normal_users
        .filter(
            approval_status="Pending"
        )
        .order_by("-date_joined")[:10]
    )

    # --------------------------------------------------------
    # RECENT DATASET UPLOADS
    # --------------------------------------------------------

    recent_datasets = (
        active_datasets
        .select_related("owner")
        .order_by("-uploaded_at")[:8]
    )

    # --------------------------------------------------------
    # RECENT DATASET COUNTS
    # --------------------------------------------------------

    users_with_datasets = (
        normal_users
        .annotate(
            dataset_count=Count(
                "datasets",
                filter=Q(
                    datasets__is_active=True
                ),
                distinct=True
            )
        )
        .filter(
            dataset_count__gt=0
        )
        .order_by("-dataset_count")[:8]
    )

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        # User statistics
        "total_users": total_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "rejected_users": rejected_users,
        "active_users": active_users,
        "inactive_users": inactive_users,

        # Dataset statistics
        "total_datasets": total_datasets,
        "dataset_type_counts": dataset_type_counts,

        # Lists
        "recent_users": recent_users,
        "pending_user_list": pending_user_list,
        "recent_datasets": recent_datasets,
        "users_with_datasets": users_with_datasets,
    }

    return render(
        request,
        "admin_dashboard/dashboard.html",
        context
    )


# ============================================================
# USER MANAGEMENT
# ============================================================

# ============================================================
# USER MANAGEMENT
# ============================================================

@admin_required
def users(request):

    user_list = (
        normal_user_queryset()
        .annotate(
            dataset_count=Count(
                "datasets",
                filter=Q(
                    datasets__is_active=True
                ),
                distinct=True
            )
        )
        .order_by("-date_joined")
    )

    # --------------------------------------------------------
    # SEARCH BY NAME
    # --------------------------------------------------------

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if search:

        user_list = user_list.filter(
            Q(first_name__icontains=search)
            |
            Q(last_name__icontains=search)
            |
            Q(username__icontains=search)
        )

    # --------------------------------------------------------
    # STATUS FILTER
    #
    # pending   = approval_status Pending
    # approved  = Approved + active
    # rejected  = approval_status Rejected
    # deactivated = Approved + inactive
    # --------------------------------------------------------

    status = request.GET.get(
        "status",
        ""
    ).strip()

    if status == "approved":

        user_list = user_list.filter(
            approval_status="Approved",
            is_active=True
        )

    elif status == "rejected":

        user_list = user_list.filter(
            approval_status="Rejected"
        )

    elif status == "deactivated":

        user_list = user_list.filter(
            approval_status="Approved",
            is_active=False
        )

    elif status == "pending":

        user_list = user_list.filter(
            approval_status="Pending"
        )

    context = {

        "users": user_list,

        "current_status": status,

        "search": search,

    }

    return render(
        request,
        "admin_dashboard/users.html",
        context
    )

# ============================================================
# USER DETAIL
# ============================================================

@admin_required
def user_detail(request, user_id):

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    # --------------------------------------------------------
    # USER DATASETS
    # --------------------------------------------------------

    user_datasets = (
        Dataset.objects
        .filter(
            owner=selected_user,
            is_active=True
        )
        .order_by("-uploaded_at")
    )

    dataset_count = user_datasets.count()

    # --------------------------------------------------------
    # DATASET VERSION COUNT
    # --------------------------------------------------------

    dataset_version_count = (
        DatasetVersion.objects
        .filter(
            dataset__owner=selected_user
        )
        .count()
    )

    # --------------------------------------------------------
    # DATASET TYPE SUMMARY
    # --------------------------------------------------------

    dataset_type_counts = (
        user_datasets
        .values("dataset_type")
        .annotate(
            total=Count("id")
        )
        .order_by("dataset_type")
    )

    context = {

        "selected_user": selected_user,

        "user_datasets": user_datasets,

        "dataset_count": dataset_count,

        "dataset_version_count": dataset_version_count,

        "dataset_type_counts": dataset_type_counts,

    }

    return render(
        request,
        "admin_dashboard/user_detail.html",
        context
    )


# ============================================================
# DATASET DETAIL
# ============================================================

@admin_required
def dataset_detail(request, dataset_id):

    dataset = get_object_or_404(
        Dataset.objects.select_related("owner"),
        id=dataset_id,
        is_active=True
    )

    # --------------------------------------------------------
    # ALL VERSIONS
    # --------------------------------------------------------

    versions = (
    DatasetVersion.objects
    .filter(dataset=dataset)
    .order_by("-version_number")
)

    # --------------------------------------------------------
    # CURRENT VERSION
    # --------------------------------------------------------

    current_version = (
        versions
        .filter(
            is_current=True
        )
        .first()
    )

    if current_version is None:

        current_version = (
            versions
            .order_by(
                "-version_number"
            )
            .first()
        )

    context = {

        "dataset": dataset,

        "versions": versions,

        "current_version": current_version,

    }

    return render(
        request,
        "admin_dashboard/dataset_detail.html",
        context
    )


# ============================================================
# APPROVE USER
# ============================================================

@admin_required
def approve_user(request, user_id):

    if request.method != "POST":

        return redirect(
            "admin_dashboard:users"
        )

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    selected_user.approval_status = "Approved"

    selected_user.is_active = True

    selected_user.save(
        update_fields=[
            "approval_status",
            "is_active",
            "updated_at"
        ]
    )

    messages.success(
        request,
        f"{selected_user.username} has been approved successfully."
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "admin_dashboard:users"
        )
    )


# ============================================================
# REJECT USER
# ============================================================

@admin_required
def reject_user(request, user_id):

    if request.method != "POST":

        return redirect(
            "admin_dashboard:users"
        )

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    selected_user.approval_status = "Rejected"

    selected_user.save(
        update_fields=[
            "approval_status",
            "updated_at"
        ]
    )

    messages.warning(
        request,
        f"{selected_user.username} has been rejected."
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "admin_dashboard:users"
        )
    )


# ============================================================
# ACTIVATE USER
# ============================================================

@admin_required
def activate_user(request, user_id):

    if request.method != "POST":

        return redirect(
            "admin_dashboard:users"
        )

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    selected_user.is_active = True

    selected_user.save(
        update_fields=[
            "is_active",
            "updated_at"
        ]
    )

    messages.success(
        request,
        f"{selected_user.username} has been activated."
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "admin_dashboard:users"
        )
    )


# ============================================================
# DEACTIVATE USER
# ============================================================

@admin_required
def deactivate_user(request, user_id):

    if request.method != "POST":

        return redirect(
            "admin_dashboard:users"
        )

    selected_user = get_object_or_404(
        User,
        id=user_id,
        is_staff=False,
        is_superuser=False
    )

    # --------------------------------------------------------
    # PREVENT SELF DEACTIVATION
    # --------------------------------------------------------

    if selected_user.id == request.user.id:

        messages.error(
            request,
            "You cannot deactivate your own account."
        )

        return redirect(
            request.META.get(
                "HTTP_REFERER",
                "admin_dashboard:users"
            )
        )

    selected_user.is_active = False

    selected_user.save(
        update_fields=[
            "is_active",
            "updated_at"
        ]
    )

    messages.warning(
        request,
        f"{selected_user.username} has been deactivated."
    )

    return redirect(
        request.META.get(
            "HTTP_REFERER",
            "admin_dashboard:users"
        )
    )