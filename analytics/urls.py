from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [

    path(
        "",
        views.business_intelligence,
        name="business_intelligence"
    ),

]