from django.urls import path

from . import views


app_name = "accounts"


urlpatterns = [

    path(
        "signup/",
        views.signup,
        name="signup"
    ),

    path(
        "signup/success/",
        views.signup_success,
        name="signup_success"
    ),

    path(
        "login/",
        views.login_view,
        name="login"
    ),

    path(
        "logout/",
        views.logout_view,
        name="logout"
    ),

]