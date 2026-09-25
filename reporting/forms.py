from django import forms

from data_management.models import Dataset, DatasetVersion

from .models import CustomReport, Report


class ReportDatasetForm(forms.Form):
    """
    Dataset and version selection used by Reporting.
    """

    dataset = forms.ModelChoiceField(
        queryset=Dataset.objects.none(),
        required=True,
        empty_label="Select Dataset",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    version = forms.ModelChoiceField(
        queryset=DatasetVersion.objects.none(),
        required=False,
        empty_label="Current Version",
        widget=forms.Select(
            attrs={
                "class": "form-select",
            }
        ),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        if user is None or not user.is_authenticated:
            return

        self.fields["dataset"].queryset = (
            Dataset.objects
            .filter(
                owner=user,
                is_active=True,
            )
            .order_by("-uploaded_at")
        )

        dataset_id = None

        if self.is_bound:
            dataset_id = self.data.get("dataset")
        else:
            dataset_id = self.initial.get("dataset")

        if dataset_id:
            self.fields["version"].queryset = (
                DatasetVersion.objects
                .filter(
                    dataset_id=dataset_id,
                )
                .order_by(
                    "-version_number",
                    "-created_at",
                )
            )


class AutomatedReportForm(ReportDatasetForm):
    """
    Form used to select the dataset for an automated report.
    """

    report_name = forms.CharField(
        max_length=255,
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Report name",
            }
        ),
    )

    report_description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Report description",
            }
        ),
    )


class CustomReportForm(ReportDatasetForm):
    """
    Initial custom-report configuration form.

    Detailed metric, dimension, filter, and chart configuration
    will be added when the Custom Reports builder is implemented.
    """

    name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Custom report name",
            }
        ),
    )

    description = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Describe this report",
            }
        ),
    )

    def __init__(self, *args, user=None, custom_report=None, **kwargs):
        super().__init__(*args, user=user, **kwargs)

        if custom_report is not None:
            self.initial.setdefault(
                "dataset",
                custom_report.dataset_id,
            )
            self.initial.setdefault(
                "version",
                custom_report.dataset_version_id,
            )
            self.initial.setdefault(
                "name",
                custom_report.name,
            )
            self.initial.setdefault(
                "description",
                custom_report.description,
            )