# kindle_dict\src\dictionary\auth_views.py

"""
Authentication views with CAPTCHA support.
"""

import logging
import secrets
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import FormView, TemplateView, UpdateView, View

from .captcha_utils import verify_captcha_response, get_captcha_context, is_captcha_enabled
from .forms import UserRegistrationForm, ProfileEditForm
from .models import UserSettings
from .email_utils import (
    send_registration_verification_email,
    send_admin_approval_notification,
    send_password_reset_email,
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


class ProfileEditView(LoginRequiredMixin, UpdateView):
    """Lets a logged-in user edit their own first/last name and email.

    Changing the email address re-triggers the verification flow from
    Sprint B.2: email_verified flips back to False, a fresh token is
    generated and a confirmation link is sent to the new address. The
    user remains logged in — the email_verified flag is only consulted
    by later sprints (password reset, email-2FA).
    """

    form_class = ProfileEditForm
    template_name = 'auth/profile.html'
    success_url = reverse_lazy('profile')

    def get_object(self, queryset=None):
        user = self.request.user
        # Snapshot the original email here. ModelForm.is_valid() copies
        # cleaned_data onto the instance *before* form_valid runs, so we
        # cannot read user.email after that point and expect the pre-edit
        # value.
        self._original_email = (user.email or '').strip().lower()
        return user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['settings_row'] = UserSettings.objects.filter(user=self.request.user).first()
        return context

    def form_valid(self, form):
        new_email = (form.cleaned_data.get('email') or '').strip().lower()
        email_changed = self._original_email != new_email

        response = super().form_valid(form)  # persists the User row

        if email_changed:
            user = self.object
            token = secrets.token_urlsafe(32)
            settings_row, _created = UserSettings.objects.get_or_create(user=user)
            settings_row.email_verified = False
            settings_row.email_verification_token = token
            settings_row.email_verification_sent_at = timezone.now()
            settings_row.save(update_fields=[
                'email_verified',
                'email_verification_token',
                'email_verification_sent_at',
                'updated_at',
            ])

            verify_url = self.request.build_absolute_uri(
                reverse('verify_email', kwargs={'token': token})
            )
            send_registration_verification_email(user, verify_url)
            messages.warning(
                self.request,
                _("Adres e-mail został zmieniony. Wysłaliśmy na nowy adres link "
                  "aktywacyjny — prosimy potwierdzić nowy adres, klikając w link.")
            )
        else:
            messages.success(self.request, _("Profil zaktualizowany."))

        return response


class PasswordResetRequestForm(forms.Form):
    """Single field 'email' form used by PasswordResetView."""

    email = forms.EmailField(
        label=_("Adres e-mail"),
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
    )


class PasswordResetView(FormView):
    """Custom password reset request that uses the project's SMTP pipeline.

    Django's built-in PasswordResetView ignores SMTPConfiguration and goes
    through django.core.mail. To keep the SMTP setup in one place — the
    runtime-configurable `SMTPConfiguration` row used by every other email
    in the app — we issue the token ourselves and send the email through
    `email_utils.send_email`.

    A reset link is only issued to accounts that are active *and* have a
    confirmed email address: a dormant or unverified account can be
    targeted with a stolen password but should not provide a way to
    bypass admin approval or hijack a contested address. To avoid leaking
    which addresses exist, the success page is shown regardless of
    whether the form's email matched anything.
    """

    form_class = PasswordResetRequestForm
    template_name = 'auth/password_reset_form.html'
    success_url = reverse_lazy('password_reset_done')

    def form_valid(self, form):
        email = (form.cleaned_data.get('email') or '').strip()
        if email:
            User = get_user_model()
            recipients = User.objects.filter(
                email__iexact=email,
                is_active=True,
                settings__email_verified=True,
            )
            for user in recipients:
                uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
                token = default_token_generator.make_token(user)
                reset_url = self.request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'uidb64': uidb64, 'token': token})
                )
                send_password_reset_email(user, reset_url)
                logger.info("Password reset link issued for user %s (id=%s)",
                            user.username, user.id)
        return super().form_valid(form)
