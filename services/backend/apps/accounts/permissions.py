from __future__ import annotations

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from common.exceptions import EmailVerificationRequiredError


class IsEmailVerified(BasePermission):
    """Require an authenticated user whose email_verified_at timestamp is set (Q5)."""

    def has_permission(self, request: Request, view: APIView) -> bool:
        del view
        user = getattr(request, "user", None)
        if user is None or not getattr(user, "is_authenticated", False):
            return False
        if getattr(user, "email_verified_at", None) is None:
            raise EmailVerificationRequiredError()
        return True


class CanSeekRoomPermission(BasePermission):
    """Require user.can_seek_room capability (Q6)."""

    message = "Account capability 'can_seek_room' is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        del view
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False) and user.can_seek_room)


class CanOfferRoomPermission(BasePermission):
    """Require user.can_offer_room capability (Q6)."""

    message = "Account capability 'can_offer_room' is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        del view
        user = getattr(request, "user", None)
        return bool(user and getattr(user, "is_authenticated", False) and user.can_offer_room)


class CanListPropertyPermission(BasePermission):
    """Require user.can_list_property capability (Q6)."""

    message = "Account capability 'can_list_property' is required."

    def has_permission(self, request: Request, view: APIView) -> bool:
        del view
        user = getattr(request, "user", None)
        return bool(
            user and getattr(user, "is_authenticated", False) and user.can_list_property
        )

