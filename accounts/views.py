from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignupForm, LoginForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render
from .forms import SignupForm, LoginForm, ChangePasswordForm
from .forms import (
    SignupForm,
    LoginForm,
    ProfileSettingsForm,
    SecuritySettingsForm,
)
from django.contrib.auth import update_session_auth_hash
def signup_view(request):

    if request.user.is_authenticated:

        if request.user.is_superuser or request.user.is_staff:
            return redirect(
                "admin_dashboard:dashboard"
            )

        return redirect(
            "core:dashboard"
        )

    if request.method == "POST":

        form = SignupForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                "Your account has been created and is waiting for admin approval."
            )

            return redirect(
                "accounts:signup_success"
            )

    else:

        form = SignupForm()

    return render(
        request,
        "accounts/signup.html",
        {
            "form": form
        }
    )

def signup_success(request):

    return render(
        request,
        "accounts/signup_success.html"
    )


def login_view(request):

    if request.user.is_authenticated:

        # ---------------------------------------------
        # ADMIN / SUPERUSER
        # ---------------------------------------------

        if (
            request.user.is_superuser
            or request.user.is_staff
        ):
            return redirect(
                "admin_dashboard:dashboard"
            )

        # ---------------------------------------------
        # NORMAL USER
        # ---------------------------------------------

        return redirect(
            "core:dashboard"
        )

    if request.method == "POST":

        form = LoginForm(request.POST)

        if form.is_valid():

            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(
                request,
                username=username,
                password=password
            )

            # ---------------------------------------------
            # INVALID LOGIN
            # ---------------------------------------------

            if user is None:

                messages.error(
                    request,
                    "Invalid username or password."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "form": form
                    }
                )

            # ---------------------------------------------
            # ADMIN / SUPERUSER
            #
            # Admin does NOT need Smart BI approval.
            # ---------------------------------------------

            if (
                user.is_superuser
                or user.is_staff
            ):

                if not user.is_active:

                    messages.error(
                        request,
                        "This administrator account is inactive."
                    )

                    return render(
                        request,
                        "accounts/login.html",
                        {
                            "form": form
                        }
                    )

                login(
                    request,
                    user
                )

                messages.success(
                    request,
                    f"Welcome back, {user.username}."
                )

                return redirect(
                    "admin_dashboard:dashboard"
                )

            # ---------------------------------------------
            # NORMAL SMART BI USER
            # ---------------------------------------------

            if not user.is_active:

                messages.error(
                    request,
                    "Your account is inactive. Please contact the administrator."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "form": form
                    }
                )

            # ---------------------------------------------
            # PENDING USER
            # ---------------------------------------------

            if user.approval_status == "Pending":

                messages.warning(
                    request,
                    "Your account is waiting for administrator approval."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "form": form
                    }
                )

            # ---------------------------------------------
            # REJECTED USER
            # ---------------------------------------------

            if user.approval_status == "Rejected":

                messages.error(
                    request,
                    "Your account has been rejected by the administrator."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {
                        "form": form
                    }
                )

            # ---------------------------------------------
            # APPROVED USER
            # ---------------------------------------------

            if user.approval_status == "Approved":

                login(
                    request,
                    user
                )

                messages.success(
                    request,
                    f"Welcome back, {user.username}."
                )

                return redirect(
                    "core:dashboard"
                )

            # ---------------------------------------------
            # FALLBACK
            # ---------------------------------------------

            messages.error(
                request,
                "Your account cannot access the system."
            )

    else:

        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )


def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect(
        "core:home"
    )
# ============================================================
# USER SETTINGS
# ============================================================

@login_required
def settings_view(request):

    return render(
        request,
        "accounts/settings.html"
    )
@login_required
def profile_settings(request):

    if request.method == "POST":

        form = ProfileSettingsForm(
            request.POST,
            request.FILES,
            instance=request.user
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your profile has been updated successfully."
            )

            return redirect(
                "accounts:profile_settings"
            )

    else:

        form = ProfileSettingsForm(
            instance=request.user
        )

    return render(
        request,
        "accounts/profile_settings.html",
        {
            "form": form,
        }
    )
@login_required
def security_settings(request):

    if request.method == "POST":

        form = ChangePasswordForm(request.POST)

        if form.is_valid():

            current_password = form.cleaned_data["current_password"]
            new_password = form.cleaned_data["new_password"]

            if not request.user.check_password(current_password):

                form.add_error(
                    "current_password",
                    "Your current password is incorrect."
                )

            else:

                request.user.set_password(new_password)
                request.user.save()

                update_session_auth_hash(
                    request,
                    request.user
                )

                messages.success(
                    request,
                    "Your password has been changed successfully."
                )

                return redirect(
                    "accounts:security_settings"
                )

    else:

        form = ChangePasswordForm()

    return render(
        request,
        "accounts/security_settings.html",
        {
            "form": form
        }
    )