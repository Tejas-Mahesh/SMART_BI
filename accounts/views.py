from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignupForm, LoginForm


def signup_view(request):

    if request.user.is_authenticated:

        if request.user.is_superuser or request.user.is_staff:
            return redirect("admin_dashboard:dashboard")

        return redirect("core:dashboard")

    if request.method == "POST":

        form = SignupForm(request.POST)

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