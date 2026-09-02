from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm

from .models import UserSettings


class LoginForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter your email",
                "autocomplete": "email",
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        )
    )


class SignupForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                "class": "form-input",
                "placeholder": "Enter your email",
                "autocomplete": "email",
            }
        )
    )

    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Create a password",
                "autocomplete": "new-password",
            }
        )
    )

    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "form-input",
                "placeholder": "Confirm your password",
                "autocomplete": "new-password",
            }
        )
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )
        return email

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            self.add_error(
                "password2",
                "Passwords do not match.",
            )
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["first_name", "last_name", "email"]

        widgets = {
            "first_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter your first name",
                    "autocomplete": "given-name",
                }
            ),
            "last_name": forms.TextInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter your last name",
                    "autocomplete": "family-name",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-input",
                    "placeholder": "Enter your email",
                    "autocomplete": "email",
                }
            ),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        existing_user = (
            User.objects.filter(email__iexact=email)
            .exclude(pk=self.instance.pk)
            .first()
        )
        if existing_user:
            raise forms.ValidationError(
                "This email address is already in use."
            )
        return email


class SettingsForm(forms.ModelForm):
    class Meta:
        model = UserSettings
        fields = [
            "email_notifications",
            "pipeline_alerts",
            "quality_alerts",
            "dashboard_auto_refresh",
        ]

        labels = {
            "email_notifications": "Email notifications",
            "pipeline_alerts": "Pipeline failure alerts",
            "quality_alerts": "Data quality alerts",
            "dashboard_auto_refresh": "Dashboard auto-refresh",
        }

        help_texts = {
            "email_notifications": "Receive important DataSentinel account notifications.",
            "pipeline_alerts": "Get notified when a pipeline execution fails.",
            "quality_alerts": "Get notified when data quality issues are detected.",
            "dashboard_auto_refresh": "Automatically refresh dashboard data when available.",
        }

        widgets = {
            "email_notifications": forms.CheckboxInput(
                attrs={"class": "settings-checkbox"}
            ),
            "pipeline_alerts": forms.CheckboxInput(
                attrs={"class": "settings-checkbox"}
            ),
            "quality_alerts": forms.CheckboxInput(
                attrs={"class": "settings-checkbox"}
            ),
            "dashboard_auto_refresh": forms.CheckboxInput(
                attrs={"class": "settings-checkbox"}
            ),
        }


class DataSentinelPasswordChangeForm(PasswordChangeForm):
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "settings-input",
                "placeholder": "Enter your current password",
                "autocomplete": "current-password",
            }
        ),
    )

    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "settings-input",
                "placeholder": "Enter your new password",
                "autocomplete": "new-password",
            }
        ),
    )

    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "settings-input",
                "placeholder": "Confirm your new password",
                "autocomplete": "new-password",
            }
        ),
    )
