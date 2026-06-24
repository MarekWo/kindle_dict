# kindle_dict\src\kindle_dict\urls.py

"""
URL configuration for kindle_dict project.
"""

from django.contrib import admin
from django.urls import path, include, reverse_lazy
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from dictionary.auth_views import (
    CaptchaLoginView,
    RegisterView,
    RegistrationDoneView,
    EmailVerificationView,
    ProfileEditView,
    PasswordResetView,
    TwoFactorSettingsView,
    OTPVerifyView,
    OTPResendCodeView,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('dictionary/', include('dictionary.urls')),

    # Ścieżki do logowania i wylogowania
    path('login/', CaptchaLoginView.as_view(next_page='/'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Rejestracja + weryfikacja e-maila
    path('accounts/register/', RegisterView.as_view(), name='register'),
    path('accounts/registration-done/', RegistrationDoneView.as_view(), name='registration_done'),
    path('accounts/verify-email/<str:token>/', EmailVerificationView.as_view(), name='verify_email'),

    # Zarządzanie własnym kontem
    path('accounts/profile/', ProfileEditView.as_view(), name='profile'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(
        template_name='auth/password_change_form.html',
        success_url=reverse_lazy('password_change_done'),
    ), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='auth/password_change_done.html',
    ), name='password_change_done'),

    # Reset zapomnianego hasła
    path('accounts/password_reset/', PasswordResetView.as_view(), name='password_reset'),
    path('accounts/password_reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html',
    ), name='password_reset_done'),
    path('accounts/reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('accounts/reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html',
    ), name='password_reset_complete'),

    # Email-based 2FA
    path('accounts/two-factor/', TwoFactorSettingsView.as_view(), name='two_factor_settings'),
    path('accounts/login/otp/', OTPVerifyView.as_view(), name='otp_verify'),
    path('accounts/login/otp/resend/', OTPResendCodeView.as_view(), name='otp_resend'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Add Django Debug Toolbar
    import debug_toolbar
    urlpatterns += [
        path('__debug__/', include(debug_toolbar.urls)),
    ]
