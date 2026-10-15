from django.urls import path

from accounts.views import auth, me

urlpatterns = [
    # CSRF
    path("csrf/", auth.CsrfView.as_view()),
    # Signup and email verification
    path("auth/signup/", auth.SignupView.as_view()),
    path("auth/verify-email/", auth.VerifyEmailView.as_view()),
    path("auth/verify-email/resend/", auth.ResendVerificationView.as_view()),
    # Login and logout
    path("auth/login/", auth.LoginView.as_view()),
    path("auth/google/", auth.GoogleLoginView.as_view()),
    path("auth/google/redirect/", auth.GoogleRedirectView.as_view()),
    path("auth/logout/", auth.LogoutView.as_view()),
    # Password
    path("auth/email-change/confirm/", auth.EmailChangeConfirmView.as_view()),
    path("auth/password/reset/", auth.PasswordResetRequestView.as_view()),
    path("auth/password/reset/confirm/", auth.PasswordResetConfirmView.as_view()),
    path("auth/password/change/", auth.PasswordChangeView.as_view()),
    # Profile
    path("me/", me.MeView.as_view()),
    path("me/email/", me.EmailChangeView.as_view()),
    path("me/avatar/", me.AvatarView.as_view()),
    path("me/tour/", me.TourView.as_view()),
    # Sessions
    path("me/sessions/", me.SessionListView.as_view()),
    path("me/sessions/<uuid:session_id>/", me.SessionDetailView.as_view()),
    # Account deletion
    path("me/delete/", me.DeleteAccountView.as_view()),
    path("me/delete/cancel/", me.CancelDeletionView.as_view()),
]
