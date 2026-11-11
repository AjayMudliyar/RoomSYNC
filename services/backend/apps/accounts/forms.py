from __future__ import annotations

from django import forms
from django.contrib.auth.forms import AdminUserCreationForm, UserChangeForm

from .models import User, normalize_email_address


class RoomSyncUserCreationForm(AdminUserCreationForm):
    """Custom Django Admin creation form bound to email-identified User model."""

    class Meta:
        model = User
        fields = ("email", "can_seek_room", "can_offer_room", "can_list_property")

    def clean_email(self) -> str:
        raw_email = str(self.cleaned_data.get("email", ""))
        normalized = normalize_email_address(raw_email)
        if not normalized:
            raise forms.ValidationError("An email address is required.")
        if User.objects.filter(email=normalized).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return normalized


class RoomSyncUserChangeForm(UserChangeForm):  # type: ignore[type-arg]
    """Custom Django Admin edit form bound to email-identified User model."""

    class Meta:
        model = User
        fields = "__all__"

    def clean_email(self) -> str:
        raw_email = str(self.cleaned_data.get("email", ""))
        normalized = normalize_email_address(raw_email)
        if not normalized:
            raise forms.ValidationError("An email address is required.")
        qs = User.objects.filter(email=normalized)
        if self.instance.pk is not None:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A user with this email already exists.")
        return normalized
