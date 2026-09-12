from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from data_management.models import Dataset


User = get_user_model()


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

        return view_function(request, *args, **kwargs)

    return wrapper


@admin_required
def dashboard(request):

    normal_users = User.objects.filter(
        is_staff=False,
        is_superuser=False
    )

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

    total_datasets = Dataset.objects.filter(
        is_active=True
    ).count()

    recent_users = normal_users.order_by(
        "-date_joined"
    )[:8]

    pending_user_list = normal_users.filter(
        approval_status="Pending"
    ).order_by(
        "-date_joined"
    )[:10]

    context = {
        "total_users": total_users,
        "pending_users": pending_users,
        "approved_users": approved_users,
        "rejected_users": rejected_users,
        "active_users": active_users,
        "inactive_users": inactive_users,
        "total_datasets": total_datasets,
        "recent_users": recent_users,
        "pending_user_list": pending_user_list,
    }

    return render(
        request,
        "admin_dashboard/dashboard.html",
        context
    )


@admin_required
def users(request):

    user_list = User.objects.filter(
        is_staff=False,
        is_superuser=False
    ).order_by("-date_joined")

    status = request.GET.get(
        "status",
        ""
    ).strip()

    user_type = request.GET.get(
        "user_type",
        ""
    ).strip()

    search = request.GET.get(
        "search",
        ""
    ).strip()

    if status:
        user_list = user_list.filter(
            approval_status=status
        )

    if user_type:
        user_list = user_list.filter(
            user_type=user_type
        )

    if search:

        from django.db.models import Q

        user_list = user_list.filter(
            Q(username__icontains=search)
            |
            Q(email__icontains=search)
            |
            Q(company_name__icontains=search)
        )

    context = {
        "users": user_list,
        "current_status": status,
        "current_user_type": user_type,
        "search": search,
    }

    return render(
        request,
        "admin_dashboard/users.html",
        context
    )


@admin_required
def user_detail(request, user_id):

    selected_user = get_object_or_404(
        User,
        id=user_id
    )

    dataset_count = Dataset.objects.filter(
        owner=selected_user,
        is_active=True
    ).count()

    context = {
        "selected_user": selected_user,
        "dataset_count": dataset_count,
    }

    return render(
        request,
        "admin_dashboard/user_detail.html",
        context
    )


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