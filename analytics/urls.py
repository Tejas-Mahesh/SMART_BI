from django.urls import path
from . import views

app_name = "analytics"

urlpatterns = [
    path("", views.business_intelligence, name="business_intelligence"),

    path("sales/", views.sales_intelligence, name="sales_intelligence"),

    path(
        "customers/",
        views.customer_intelligence,
        name="customer_intelligence",
    ),

    path(
        "customers/detail/",
        views.customer_detail,
        name="customer_detail",
    ),

    path(
        "products/",
        views.product_intelligence,
        name="product_intelligence",
    ),

    path(
        "regional/",
        views.regional_intelligence,
        name="regional_intelligence",
    ),

    path(
        "financial/",
        views.financial_intelligence,
        name="financial_intelligence",
    ),

    path(
        "marketing/",
        views.marketing_intelligence,
        name="marketing_intelligence",
    ),

    path(
        "returns/",
        views.returns_intelligence,
        name="returns_intelligence",
    ),
]