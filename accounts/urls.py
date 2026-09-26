from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [

    path(
        "signup/",
        views.signup_view,
        name="signup",
    ),

    path(
        "signup/success/",
        views.signup_success,
        name="signup_success",
    ),

    path(
        "login/",
        views.login_view,
        name="login",
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout",
    ),
        path(
        "settings/",
        views.settings_view,
        name="settings",
    ),

    path(
        "settings/profile/",
        views.profile_settings,
        name="profile_settings",
    ),

path(
    "settings/security/",
    views.security_settings,
    name="security_settings",
),
]

