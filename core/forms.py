from django import forms

from .models import ContactMessage


class ContactMessageForm(forms.ModelForm):

    class Meta:
        model = ContactMessage

        fields = [
            "name",
            "email",
            "subject",
            "message",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "id": "contactName",
                    "class": "cnt-input",
                    "placeholder": "Your name",
                    "autocomplete": "name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "id": "contactEmail",
                    "class": "cnt-input",
                    "placeholder": "Your corporate email address",
                    "autocomplete": "email",
                }
            ),

            "subject": forms.TextInput(
                attrs={
                    "id": "contactSubject",
                    "class": "cnt-input",
                    "placeholder": "How can we help?",
                }
            ),

            "message": forms.Textarea(
                attrs={
                    "id": "contactMessage",
                    "class": "cnt-textarea",
                    "placeholder": "Write your message or inquiry here...",
                    "rows": 6,
                }
            ),
        }

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if len(name) < 2:
            raise forms.ValidationError(
                "Please enter your name (minimum 2 characters)."
            )

        return name

    def clean_subject(self):
        subject = self.cleaned_data["subject"].strip()

        if len(subject) < 3:
            raise forms.ValidationError(
                "Please enter a subject (minimum 3 characters)."
            )

        return subject

    def clean_message(self):
        message = self.cleaned_data["message"].strip()

        if len(message) < 10:
            raise forms.ValidationError(
                "Please enter a message (minimum 10 characters)."
            )

        return message