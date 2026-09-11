from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import SignupForm, LoginForm


def signup(request):

    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":

        form = SignupForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Your account has been created successfully. "
                "Please wait for administrator approval before logging in."
            )

            return redirect("accounts:signup_success")

    else:
        form = SignupForm()

    return render(
        request,
        "accounts/signup.html",
        {"form": form}
    )


def signup_success(request):
    return render(
        request,
        "accounts/signup_success.html"
    )


def login_view(request):

    if request.user.is_authenticated:
        return redirect("core:dashboard")

    form = LoginForm(request.POST or None)

    if request.method == "POST":

        if form.is_valid():

            username = form.cleaned_data["username"]
            password = form.cleaned_data["password"]

            user = authenticate(
                request=request,
                username=username,
                password=password
            )

            # -----------------------------------------
            # INVALID LOGIN
            # -----------------------------------------

            if user is None:

                messages.error(
                    request,
                    "Invalid username or password."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {"form": form}
                )

            # -----------------------------------------
            # PENDING APPROVAL
            # -----------------------------------------

            if user.approval_status == "Pending":

                messages.warning(
                    request,
                    "Admin has not approved your account yet. "
                    "Please wait for administrator approval."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {"form": form}
                )

            # -----------------------------------------
            # REJECTED
            # -----------------------------------------

            if user.approval_status == "Rejected":

                messages.error(
                    request,
                    "Your account has been rejected by the administrator."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {"form": form}
                )

            # -----------------------------------------
            # INACTIVE
            # -----------------------------------------

            if not user.is_active:

                messages.error(
                    request,
                    "Your account is inactive. Please contact the administrator."
                )

                return render(
                    request,
                    "accounts/login.html",
                    {"form": form}
                )

            # -----------------------------------------
            # APPROVED
            # -----------------------------------------

            if user.approval_status == "Approved":

                login(request, user)

                messages.success(
                    request,
                    f"Welcome back, {user.username}!"
                )

                return redirect("core:dashboard")

            # -----------------------------------------
            # UNKNOWN STATUS
            # -----------------------------------------

            messages.error(
                request,
                "Your account status is invalid. Please contact the administrator."
            )

            return render(
                request,
                "accounts/login.html",
                {"form": form}
            )

    return render(
        request,
        "accounts/login.html",
        {"form": form}
    )


@login_required
def logout_view(request):

    logout(request)

    messages.success(
        request,
        "You have been logged out successfully."
    )

    return redirect("core:home")