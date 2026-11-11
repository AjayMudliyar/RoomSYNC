from django.urls import path

from .views import (
    CsrfTokenView,
    EmailResendView,
    EmailVerifyView,
    GoogleAuthView,
    GoogleLinkView,
    LoginView,
    LogoutView,
    MeDataExportView,
    MeDeletionRequestView,
    MeSessionDetailView,
    MeSessionsView,
    MeView,
    PasswordChangeView,
    PasswordForgotView,
    PasswordResetView,
    RefreshView,
    RegisterView,
)

urlpatterns = [
    path("auth/csrf", CsrfTokenView.as_view(), name="auth-csrf"),
    path("auth/register", RegisterView.as_view(), name="auth-register"),
    path("auth/login", LoginView.as_view(), name="auth-login"),
    path("auth/google", GoogleAuthView.as_view(), name="auth-google"),
    path("auth/google/link", GoogleLinkView.as_view(), name="auth-google-link"),
    path("auth/refresh", RefreshView.as_view(), name="auth-refresh"),
    path("auth/logout", LogoutView.as_view(), name="auth-logout"),
    path("auth/email/verify", EmailVerifyView.as_view(), name="auth-email-verify"),
    path("auth/email/resend", EmailResendView.as_view(), name="auth-email-resend"),
    path("auth/password/forgot", PasswordForgotView.as_view(), name="auth-password-forgot"),
    path("auth/password/reset", PasswordResetView.as_view(), name="auth-password-reset"),
    path("auth/password/change", PasswordChangeView.as_view(), name="auth-password-change"),
    path("me", MeView.as_view(), name="me"),
    path("me/sessions", MeSessionsView.as_view(), name="me-sessions"),
    path("me/sessions/<uuid:session_id>", MeSessionDetailView.as_view(), name="me-session-detail"),
    path("me/deletion-request", MeDeletionRequestView.as_view(), name="me-deletion-request"),
    path("me/data-export", MeDataExportView.as_view(), name="me-data-export"),
]

