from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser


class SignupForm(forms.ModelForm):

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Create a password"
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm your password"
            }
        )
    )

    class Meta:
        model = CustomUser

        fields = [
            "first_name",
            "last_name",
            "username",
            "email",
            "company_name",
            "phone_number",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={"placeholder": "First name"}
            ),

            "last_name": forms.TextInput(
                attrs={"placeholder": "Last name"}
            ),

            "username": forms.TextInput(
                attrs={"placeholder": "Choose a username"}
            ),

            "email": forms.EmailInput(
                attrs={"placeholder": "Business email"}
            ),

            "company_name": forms.TextInput(
                attrs={"placeholder": "Company name"}
            ),

            "phone_number": forms.TextInput(
                attrs={"placeholder": "Phone number"}
            ),
        }

    def clean_username(self):
        username = self.cleaned_data["username"]

        if CustomUser.objects.filter(
            username=username
        ).exists():
            raise forms.ValidationError(
                "This username is already registered."
            )

        return username

    def clean_email(self):
        email = self.cleaned_data["email"]

        if CustomUser.objects.filter(
            email=email
        ).exists():
            raise forms.ValidationError(
                "This email is already registered."
            )

        return email

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get(
            "confirm_password"
        )

        if password and confirm_password:

            if password != confirm_password:
                raise forms.ValidationError(
                    "Passwords do not match."
                )

        return cleaned_data

    def save(self, commit=True):

        user = super().save(commit=False)

        user.set_password(
            self.cleaned_data["password"]
        )

        user.approval_status = (
            CustomUser.APPROVAL_PENDING
        )

        if commit:
            user.save()

        return user


from django import forms

from .models import CustomUser


class LoginForm(forms.Form):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your username",
                "autocomplete": "username",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        )
    )