from django import forms

from .models import Dataset


class DatasetUploadForm(forms.ModelForm):

    class Meta:
        model = Dataset

        fields = [
            "name",
            "dataset_type",
            "file",
        ]

        widgets = {

            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Example: January Sales Data",
                }
            ),

            "dataset_type": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "file": forms.ClearableFileInput(
                attrs={
                    "class": "file-input",
                    "accept": ".csv,.xls,.xlsx",
                }
            ),
        }

    def clean_file(self):

        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            raise forms.ValidationError(
                "Please select a dataset file."
            )

        filename = uploaded_file.name.lower()

        allowed_extensions = [
            ".csv",
            ".xls",
            ".xlsx",
        ]

        if not any(
            filename.endswith(extension)
            for extension in allowed_extensions
        ):
            raise forms.ValidationError(
                "Only CSV, XLS and XLSX files are allowed."
            )

        # 20 MB maximum
        max_size = 20 * 1024 * 1024

        if uploaded_file.size > max_size:
            raise forms.ValidationError(
                "File size cannot exceed 20 MB."
            )

        return uploaded_file