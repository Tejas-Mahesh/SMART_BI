from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from .models import ContactMessage


# ============================================================
# PUBLIC PAGES
# ============================================================

def home(request):
    return render(
        request,
        "core/home.html"
    )


def about(request):
    return render(
        request,
        "core/about.html"
    )


def how_it_works(request):
    return render(
        request,
        "core/how_it_works.html"
    )


def features(request):
    return render(
        request,
        "core/feature.html"
    )


def contact(request):

    if request.method == "POST":

        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        # ----------------------------------------------------
        # BASIC VALIDATION
        # ----------------------------------------------------

        if len(name) < 2:
            messages.error(
                request,
                "Please enter a valid name."
            )
            return redirect("core:contact")

        if not email:
            messages.error(
                request,
                "Please enter your email address."
            )
            return redirect("core:contact")

        if len(subject) < 3:
            messages.error(
                request,
                "Please enter a valid subject."
            )
            return redirect("core:contact")

        if len(message) < 10:
            messages.error(
                request,
                "Please enter a message of at least 10 characters."
            )
            return redirect("core:contact")

        # ----------------------------------------------------
        # SAVE CONTACT MESSAGE
        # ----------------------------------------------------

        ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
        )

        # ----------------------------------------------------
        # SUCCESS
        # ----------------------------------------------------

        messages.success(
            request,
            "Your message has been sent successfully. "
            "We will get back to you soon."
        )

        return redirect("core:contact")

    return render(
        request,
        "core/contact.html"
    )


# ============================================================
# EXECUTIVE DASHBOARD
# ============================================================

@login_required
def dashboard(request):

    # ========================================================
    # CURRENT TIME
    # ========================================================

    current_hour = timezone.localtime().hour

    if 5 <= current_hour < 12:
        greeting = "Good Morning"
        greeting_icon = "🌅"

    elif 12 <= current_hour < 17:
        greeting = "Good Afternoon"
        greeting_icon = "☀️"

    elif 17 <= current_hour < 21:
        greeting = "Good Evening"
        greeting_icon = "🌆"

    else:
        greeting = "Good Night"
        greeting_icon = "🌙"

    # ========================================================
    # USER DISPLAY NAME
    # ========================================================

    user = request.user

    if user.first_name:
        display_name = user.first_name

    elif user.get_full_name():
        display_name = user.get_full_name()

    elif user.username:
        display_name = user.username

    else:
        display_name = "User"

    # ========================================================
    # DATA MANAGEMENT
    # ========================================================
    #
    # IMPORTANT:
    # These URL names MUST match data_management/urls.py
    #
    # upload_data
    # dataset_management
    # quality
    # cleaning
    # validation
    # profiling
    # transformation
    # version_history
    #
    # ========================================================

    data_management_links = [

        {
            "title": "Upload Data",
            "description": "Add new business data to the system.",
            "icon": "upload",
            "url": "data_management:upload_data",
        },

        {
            "title": "Dataset Management",
            "description": "Manage and organize your datasets.",
            "icon": "database",
            "url": "data_management:dataset_management",
        },

        {
            "title": "Data Quality",
            "description": "Review and monitor data quality.",
            "icon": "quality",
            "url": "data_management:quality",
        },

        {
            "title": "Data Cleaning",
            "description": "Clean and prepare business data.",
            "icon": "cleaning",
            "url": "data_management:cleaning",
        },

    ]

    # ========================================================
    # BUSINESS ANALYTICS
    # ========================================================

    analytics_links = [

    {
        "title": "Business Intelligence",
        "description": "Understand overall business performance.",
        "icon": "business",
        "url": "analytics:business_intelligence",
    },

    {
        "title": "Sales Intelligence",
        "description": "Explore sales performance and trends.",
        "icon": "sales",
        "url": "analytics:sales_intelligence",
    },

    {
        "title": "Customer Intelligence",
        "description": "Understand customers and their behavior.",
        "icon": "customer",
        "url": "analytics:customer_intelligence",
    },

    {
        "title": "Product Intelligence",
        "description": "Analyze products and product performance.",
        "icon": "product",
        "url": "analytics:product_intelligence",
    },

    {
        "title": "Regional Intelligence",
        "description": "Explore performance across regions.",
        "icon": "regional",
        "url": "analytics:regional_intelligence",
    },

    {
        "title": "Marketing Intelligence",
        "description": "Analyze marketing activities and channels.",
        "icon": "marketing",
        "url": "analytics:marketing_intelligence",
    },

    {
        "title": "Financial Intelligence",
        "description": "Explore financial performance and trends.",
        "icon": "financial",
        "url": "analytics:financial_intelligence",
    },

    {
        "title": "Returns Intelligence",
        "description": "Understand returns and return patterns.",
        "icon": "returns",
        "url": "analytics:returns_intelligence",
    },

]

    # ========================================================
    # ADVANCED INSIGHTS
    # ========================================================

    insight_links = [

        {
            "title": "Future Trends",
            "description":
                "Discover emerging patterns and trends.",
            "icon": "trends",
            "url":
                "advanced_insights:future_trends",
        },

        {
            "title": "Forecasting",
            "description":
                "Generate forecasts from business data.",
            "icon": "forecast",
            "url":
                "advanced_insights:forecasting",
        },

        {
            "title": "Anomaly Detection",
            "description":
                "Identify unusual business behavior.",
            "icon": "anomaly",
            "url":
                "advanced_insights:anomaly_detection",
        },

        {
            "title": "Root Cause Analysis",
            "description":
                "Investigate the causes behind business changes.",
            "icon": "root-cause",
            "url":
                "advanced_insights:root_cause_analysis",
        },

        {
            "title": "Customer Segmentation",
            "description":
                "Discover meaningful customer groups.",
            "icon": "segmentation",
            "url":
                "advanced_insights:customer_segmentation",
        },

        {
            "title": "Churn / Risk Analysis",
            "description":
                "Identify customer and business risks.",
            "icon": "risk",
            "url":
                "advanced_insights:churn_risk",
        },

        {
            "title": "Opportunity Detection",
            "description":
                "Discover potential business opportunities.",
            "icon": "opportunity",
            "url":
                "advanced_insights:opportunity_detection",
        },

    ]

    # ========================================================
    # DECISION INTELLIGENCE
    # ========================================================

    decision_links = [

        {
            "title": "Recommendations",
            "description":
                "Turn insights into recommended actions.",
            "icon": "recommendation",
            "url":
                "decision_intelligence:recommendations",
        },

        {
            "title": "What-If Simulator",
            "description":
                "Explore possible business outcomes.",
            "icon": "what-if",
            "url":
                "decision_intelligence:what_if",
        },

        {
            "title": "Scenario Planning",
            "description":
                "Compare different business scenarios.",
            "icon": "scenario",
            "url":
                "decision_intelligence:scenario_planning",
        },

        {
            "title": "Business Alerts",
            "description":
                "Monitor important business events.",
            "icon": "alerts",
            "url":
                "decision_intelligence:business_alerts",
        },

        {
            "title": "Action Center",
            "description":
                "Track and manage recommended actions.",
            "icon": "action",
            "url":
                "decision_intelligence:action_center",
        },

        {
            "title": "Decision Impact",
            "description":
                "Understand the impact of decisions.",
            "icon": "impact",
            "url":
                "decision_intelligence:decision_impact",
        },

    ]

    # ========================================================
    # REPORTING
    # ========================================================

    reporting_links = [

        {
            "title": "Automated Reports",
            "description":
                "Generate automated business reports.",
            "icon": "automated-report",
            "url":
                "reporting:automated_reports",
        },

        {
            "title": "Custom Reports",
            "description":
                "Create reports based on your requirements.",
            "icon": "custom-report",
            "url":
                "reporting:custom_reports",
        },

        {
            "title": "Export PDF",
            "description":
                "Export business reports as PDF.",
            "icon": "pdf",
            "url":
                "reporting:export_pdf",
        },

        {
            "title": "Export Excel",
            "description":
                "Export business data and reports to Excel.",
            "icon": "excel",
            "url":
                "reporting:export_excel",
        },

        {
            "title": "Report History",
            "description":
                "View previously generated reports.",
            "icon": "history",
            "url":
                "reporting:report_history",
        },

    ]

    # ========================================================
    # DASHBOARD CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # HEADER
        # ----------------------------------------------------

        "dashboard_title":
            "Executive Dashboard",

        "dashboard_subtitle":
            "Your intelligent business management workspace",

        "greeting":
            greeting,

        "greeting_icon":
            greeting_icon,

        "display_name":
            display_name,

        # ----------------------------------------------------
        # NAVIGATION SECTIONS
        # ----------------------------------------------------

        "data_management_links":
            data_management_links,

        "analytics_links":
            analytics_links,

        "insight_links":
            insight_links,

        "decision_links":
            decision_links,

        "reporting_links":
            reporting_links,

    }

    # ========================================================
    # RENDER
    # ========================================================

    return render(
        request,
        "core/dashboard.html",
        context
    )