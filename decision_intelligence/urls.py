from django.urls import path

from . import views


app_name = "decision_intelligence"


urlpatterns = [
    path(
        "recommendations/",
        views.recommendations,
        name="recommendations",
    ),
]