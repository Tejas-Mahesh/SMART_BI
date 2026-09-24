from django.urls import path

from analytics.views.dashboard_views import executive_dashboard

from analytics.views.sales import sales_intelligence
from analytics.views.customer import customer_intelligence
from analytics.views.product import product_intelligence
from analytics.views.regional import regional_intelligence
from analytics.views.marketing import marketing_intelligence
from analytics.views.financial import financial_intelligence
from analytics.views.returns import returns_intelligence
from analytics.views.business import business_intelligence

app_name = "analytics"
urlpatterns = [

    # Executive Dashboard
  path(
    "dashboard/",
    executive_dashboard,
    name="executive_dashboard",
),

    # Sales Intelligence
    path(
        "sales/",
        sales_intelligence,
        name="sales_intelligence",
    ),

    # Customer Intelligence
    path(
        "customers/",
        customer_intelligence,
        name="customer_intelligence",
    ),

    # Product Intelligence
    path(
        "products/",
        product_intelligence,
        name="product_intelligence",
    ),

    # Regional Intelligence
    path(
        "regional/",
        regional_intelligence,
        name="regional_intelligence",
    ),

    # Marketing Intelligence
    path(
        "marketing/",
        marketing_intelligence,
        name="marketing_intelligence",
    ),

    # Financial Intelligence
    path(
        "financial/",
        financial_intelligence,
        name="financial_intelligence",
    ),

    # Returns Intelligence
    path(
        "returns/",
        returns_intelligence,
        name="returns_intelligence",
    ),

    # Business Intelligence
    path(
        "business/",
        business_intelligence,
        name="business_intelligence",
    ),
]