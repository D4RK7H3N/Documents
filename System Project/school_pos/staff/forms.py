from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class StaffRegisterForm(UserCreationForm):
    class Meta:
        model = User
        fields = ["username", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': field.label
            })


class StaffLoginForm(AuthenticationForm):
    """
    Simple login form - case-insensitive logic handled by authentication backend.
    Custom error message without case-sensitive warning.
    """
    # Override error messages to remove case-sensitive warning
    error_messages = {
        'invalid_login': (
            "Invalid username or password. Please try again."
        ),
        'inactive': "This account is inactive.",
    }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Username (case-insensitive)'
        })
        self.fields['password'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Password'
        })