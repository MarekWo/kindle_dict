# kindle_dict\src\dictionary\auth_views.py

"""
Authentication views with CAPTCHA support.
"""

import logging
import secrets
from datetime import timedelta

from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView, View

from .captcha_utils import verify_captcha_response, get_captcha_context, is_captcha_enabled
from .forms import UserRegistrationForm
from .models import UserSettings
from .email_utils import (
    send_registration_verification_email,
    send_admin_approval_notification,
)

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_TOKEN_TTL = timedelta(hours=48)


class CaptchaAuthenticationForm(AuthenticationForm):
    """Authentication form with CAPTCHA support"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add Bootstrap classes to form fields
        for field in self.fields.values():
            if isinstance(field.widget, forms.TextInput) or isinstance(field.widget, forms.PasswordInput):
                field.widget.attrs.update({'class': 'form-control'})


class CaptchaLoginView(LoginView):
    """Login view with CAPTCHA support"""

    form_class = CaptchaAuthenticationForm
    template_name = 'auth/login.html'

    def get_context_data(self, **kwargs):
        """Add CAPTCHA context data"""
        context = super().get_context_data(**kwargs)
        context.update(get_captcha_context('login'))
        return context

    def form_valid(self, form):
        """Verify CAPTCHA before login"""
        # Verify CAPTCHA if enabled
        if is_captcha_enabled('login'):
            captcha_response = self.request.POST.get('cf-turnstile-response') or self.request.POST.get('g-recaptcha-response')
            if not verify_captcha_response(captcha_response):
                form.add_error(None, _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie."))
                context = self.get_context_data(form=form)
                context['captcha_error'] = _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie.")
                return self.render_to_response(context)

        return super().form_valid(form)


class RegisterView(FormView):
    """Self-registration: collect credentials, send confirmation email."""

    form_class = UserRegistrationForm
    template_name = 'auth/register.html'
    success_url = reverse_lazy('registration_done')

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            messages.info(request, _("Jesteś już zalogowany."))
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(get_captcha_context('register'))
        return context

    def form_valid(self, form):
        # CAPTCHA gate (reuses the project's Cloudflare Turnstile / reCAPTCHA setup)
        if is_captcha_enabled('register'):
            captcha_response = self.request.POST.get('cf-turnstile-response') or self.request.POST.get('g-recaptcha-response')
            if not verify_captcha_response(captcha_response):
                form.add_error(None, _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie."))
                context = self.get_context_data(form=form)
                context['captcha_error'] = _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie.")
                return self.render_to_response(context)

        # Create the user as inactive; the post_save signal creates UserSettings.
        user = form.save(commit=False)
        user.is_active = False
        user.save()

        # Stash the verification token on the auto-created UserSettings row.
        token = secrets.token_urlsafe(32)
        settings_row = UserSettings.objects.get(user=user)
        settings_row.email_verification_token = token
        settings_row.email_verification_sent_at = timezone.now()
        settings_row.save(update_fields=[
            'email_verification_token',
            'email_verification_sent_at',
            'updated_at',
        ])

        verify_url = self.request.build_absolute_uri(
            reverse('verify_email', kwargs={'token': token})
        )
        send_registration_verification_email(user, verify_url)

        return super().form_valid(form)


class RegistrationDoneView(TemplateView):
    """Render the post-registration 'check your inbox' page."""
    template_name = 'auth/registration_done.html'


class EmailVerificationView(View):
    """Consume the email verification token from the link in the email."""

    def get(self, request, token, *args, **kwargs):
        settings_row = UserSettings.objects.filter(
            email_verification_token=token
        ).select_related('user').first()

        if settings_row is None:
            return render(request, 'auth/email_verification_failed.html', {
                'reason': 'invalid',
            })

        sent_at = settings_row.email_verification_sent_at
        if sent_at is None or (timezone.now() - sent_at) > EMAIL_VERIFICATION_TOKEN_TTL:
            return render(request, 'auth/email_verification_failed.html', {
                'reason': 'expired',
            })

        if not settings_row.email_verified:
            settings_row.email_verified = True
            settings_row.email_verification_token = None
            settings_row.save(update_fields=[
                'email_verified',
                'email_verification_token',
                'updated_at',
            ])
            approval_url = request.build_absolute_uri(
                reverse('dictionary:user_approval_detail', kwargs={'pk': settings_row.user.pk})
            )
            send_admin_approval_notification(settings_row.user, approval_url=approval_url)
            logger.info(
                "Email verified for user %s (id=%s); awaiting admin approval",
                settings_row.user.username, settings_row.user.id,
            )
        else:
            settings_row.email_verification_token = None
            settings_row.save(update_fields=[
                'email_verification_token',
                'updated_at',
            ])

        return render(request, 'auth/email_verified.html', {
            'user': settings_row.user,
        })
