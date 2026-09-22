from django.urls import path

from . import views


app_name = "admin_dashboard"


urlpatterns = [

    # ========================================================
    # DASHBOARD
    # ========================================================

    path(
        "",
        views.dashboard,
        name="dashboard",
    ),

    # ========================================================
    # USERS
    # ========================================================

    path(
        "users/",
        views.users,
        name="users",
    ),

    path(
        "users/<int:user_id>/",
        views.user_detail,
        name="user_detail",
    ),

    # ========================================================
    # USER ACTIONS
    # ========================================================

    path(
        "users/<int:user_id>/approve/",
        views.approve_user,
        name="approve_user",
    ),

    path(
        "users/<int:user_id>/reject/",
        views.reject_user,
        name="reject_user",
    ),

    path(
        "users/<int:user_id>/activate/",
        views.activate_user,
        name="activate_user",
    ),

    path(
        "users/<int:user_id>/deactivate/",
        views.deactivate_user,
        name="deactivate_user",
    ),

    # ========================================================
    # DATASETS
    # ========================================================

    path(
        "datasets/<int:dataset_id>/",
        views.dataset_detail,
        name="dataset_detail",
    ),
]