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
            "business_logo",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name"
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Last name"
                }
            ),

            "username": forms.TextInput(
                attrs={
                    "placeholder": "Choose a username"
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Business email"
                }
            ),

            "company_name": forms.TextInput(
                attrs={
                    "placeholder": "Company name"
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "Phone number"
                }
            ),

            "business_logo": forms.ClearableFileInput(
                attrs={
                    "accept": "image/png,image/jpeg,image/jpg"
                }
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
        confirm_password = cleaned_data.get("confirm_password")

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

from django import forms

from .models import CustomUser


class LoginForm(forms.Form):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Enter username",
                "autocomplete": "username",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        )
    )

# ============================================================
# PROFILE SETTINGS FORM
# ============================================================

class ProfileSettingsForm(forms.ModelForm):

    class Meta:
        model = CustomUser

        fields = [
            "first_name",
            "last_name",
            "email",
            "company_name",
            "phone_number",
            "business_logo",
        ]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "placeholder": "First name",
                    "autocomplete": "given-name",
                }
            ),

            "last_name": forms.TextInput(
                attrs={
                    "placeholder": "Last name",
                    "autocomplete": "family-name",
                }
            ),

            "email": forms.EmailInput(
                attrs={
                    "placeholder": "Business email",
                    "autocomplete": "email",
                }
            ),

            "company_name": forms.TextInput(
                attrs={
                    "placeholder": "Company name",
                    "autocomplete": "organization",
                }
            ),

            "phone_number": forms.TextInput(
                attrs={
                    "placeholder": "Phone number",
                    "autocomplete": "tel",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"]

        if CustomUser.objects.filter(
            email=email
        ).exclude(
            pk=self.instance.pk
        ).exists():
            raise forms.ValidationError(
                "This email is already registered."
            )

        return email
# ============================================================
# SECURITY SETTINGS FORM
# ============================================================

class SecuritySettingsForm(forms.Form):

    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your current password",
                "autocomplete": "current-password",
            }
        )
    )

    new_password = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter your new password",
                "autocomplete": "new-password",
            }
        )
    )

    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm your new password",
                "autocomplete": "new-password",
            }
        )
    )

    def __init__(self, *args, user=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.user = user

    def clean_current_password(self):

        current_password = self.cleaned_data.get(
            "current_password"
        )

        if self.user and not self.user.check_password(
            current_password
        ):
            raise forms.ValidationError(
                "Your current password is incorrect."
            )

        return current_password

    def clean(self):

        cleaned_data = super().clean()

        new_password = cleaned_data.get(
            "new_password"
        )

        confirm_password = cleaned_data.get(
            "confirm_password"
        )

        if (
            new_password
            and confirm_password
            and new_password != confirm_password
        ):
            raise forms.ValidationError(
                "New passwords do not match."
            )

        return cleaned_data

from django import forms
from django.contrib.auth.password_validation import validate_password


from django import forms
from django.contrib.auth.password_validation import validate_password


class ChangePasswordForm(forms.Form):

    current_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter current password",
                "autocomplete": "current-password",
            }
        ),
    )

    new_password = forms.CharField(
        label="New Password",
        validators=[validate_password],
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Enter new password",
                "autocomplete": "new-password",
            }
        ),
    )

    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(
            attrs={
                "placeholder": "Confirm new password",
                "autocomplete": "new-password",
            }
        ),
    )

    def clean(self):
        cleaned_data = super().clean()

        new_password = cleaned_data.get("new_password")
        confirm_password = cleaned_data.get("confirm_password")

        if new_password and confirm_password:
            if new_password != confirm_password:
                raise forms.ValidationError(
                    "New passwords do not match."
                )

        return cleaned_data