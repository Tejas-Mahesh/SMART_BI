from django.contrib.auth.decorators import login_required
from django.shortcuts import render


def home(request):
    return render(request, "core/home.html")


def about(request):
    return render(request, "core/about.html")


def how_it_works(request):
    return render(request, "core/how_it_works.html")


def contact(request):
    return render(request, "core/contact.html")


@login_required
def dashboard(request):

    # Extra safety:
    # Only approved users can access the platform.

    if request.user.approval_status != "Approved":
        return render(
            request,
            "accounts/access_denied.html",
            {
                "message": (
                    "Your account has not been approved "
                    "by the administrator yet."
                )
            }
        )

    return render(
        request,
        "dashboard/dashboard.html"
    )