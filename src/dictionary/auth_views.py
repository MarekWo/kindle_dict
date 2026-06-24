# kindle_dict\src\dictionary\auth_views.py

"""
Authentication views with CAPTCHA support.
"""

import logging
import secrets
import time
from datetime import timedelta

from django.contrib.auth import get_user_model, login as auth_login
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
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
from .forms import UserRegistrationForm, ProfileEditForm, EmailOTPForm
from .models import UserSettings
from .email_utils import (
    send_registration_verification_email,
    send_admin_approval_notification,
    send_password_reset_email,
    send_two_factor_code,
)

logger = logging.getLogger(__name__)

EMAIL_VERIFICATION_TOKEN_TTL = timedelta(hours=48)

# Email-2FA constants
OTP_CACHE_TTL_SECONDS = 600          # 10 min for a fresh code to be valid
OTP_SESSION_TIMEOUT_SECONDS = 900    # 15 min between password and OTP submit
OTP_MAX_ATTEMPTS = 3
OTP_RESEND_MIN_INTERVAL_SECONDS = 60


def _generate_otp_code():
    """Six-digit numeric code, e.g. '048213'."""
    return f"{secrets.randbelow(1_000_000):06d}"


def _issue_otp_for(user, request, *, purpose):
    """Generate an OTP, cache it under (purpose, user.id), email it.

    `purpose` distinguishes cache keys between the login flow ('login')
    and the opt-in confirmation step ('enable_2fa') so the two never
    collide if a user opens both at once.
    """
    code = _generate_otp_code()
    cache_key = f"otp:{purpose}:{user.pk}"
    cache.set(cache_key, code, timeout=OTP_CACHE_TTL_SECONDS)
    send_two_factor_code(user, code)
    logger.info("Issued OTP for user %s (purpose=%s)", user.username, purpose)
    return cache_key


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
        """Verify CAPTCHA, then either log in or hand off to email-2FA."""
        # Verify CAPTCHA if enabled
        if is_captcha_enabled('login'):
            captcha_response = self.request.POST.get('cf-turnstile-response') or self.request.POST.get('g-recaptcha-response')
            if not verify_captcha_response(captcha_response):
                form.add_error(None, _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie."))
                context = self.get_context_data(form=form)
                context['captcha_error'] = _("Weryfikacja CAPTCHA nie powiodła się. Spróbuj ponownie.")
                return self.render_to_response(context)

        user = form.get_user()
        try:
            settings_row = user.settings
        except UserSettings.DoesNotExist:
            settings_row = None

        if settings_row and settings_row.two_factor_enabled:
            # Defer login until the OTP is verified. Park the user.id and the
            # post-login redirect in the session; OTPVerifyView picks them up.
            _issue_otp_for(user, self.request, purpose='login')
            self.request.session['otp_pending_user_id'] = user.pk
            self.request.session['otp_pending_started_at'] = int(time.time())
            self.request.session['otp_pending_attempts'] = 0
            self.request.session['otp_pending_next'] = self.get_success_url()
            return redirect('otp_verify')

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


class TwoFactorSettingsView(LoginRequiredMixin, View):
    """Toggle email-based 2FA for the logged-in user.

    Three actions, all POST:
    - 'start_enable'   — generate + email a confirmation code, show OTP form
    - 'confirm_enable' — validate code, flip two_factor_enabled=True
    - 'disable'        — flip two_factor_enabled=False (no confirmation)

    GET shows the current state and the relevant button.
    """

    template_name = 'auth/two_factor_settings.html'
    enable_cache_purpose = 'enable_2fa'

    def get_settings(self):
        settings_row, _created = UserSettings.objects.get_or_create(user=self.request.user)
        return settings_row

    def render(self, *, settings_row, otp_form=None, awaiting_code=False, message=None):
        return render(self.request, self.template_name, {
            'settings_row': settings_row,
            'otp_form': otp_form or EmailOTPForm(),
            'awaiting_code': awaiting_code,
            'message': message,
        })

    def get(self, request):
        return self.render(settings_row=self.get_settings())

    def post(self, request):
        settings_row = self.get_settings()
        action = request.POST.get('action')

        if action == 'start_enable':
            if settings_row.two_factor_enabled:
                messages.info(request, _("Email-2FA jest już włączone."))
                return redirect('two_factor_settings')
            _issue_otp_for(request.user, request, purpose=self.enable_cache_purpose)
            messages.info(
                request,
                _("Wysłaliśmy kod potwierdzający na Twój adres e-mail. "
                  "Wprowadź go, aby włączyć weryfikację dwustopniową.")
            )
            return self.render(settings_row=settings_row, awaiting_code=True)

        if action == 'confirm_enable':
            otp_form = EmailOTPForm(request.POST)
            if not otp_form.is_valid():
                return self.render(settings_row=settings_row, otp_form=otp_form, awaiting_code=True)
            cache_key = f"otp:{self.enable_cache_purpose}:{request.user.pk}"
            expected = cache.get(cache_key)
            entered = otp_form.cleaned_data['code']
            if not expected or not secrets.compare_digest(expected, entered):
                otp_form.add_error('code', _("Nieprawidłowy lub wygasły kod. Wygeneruj nowy."))
                return self.render(settings_row=settings_row, otp_form=otp_form, awaiting_code=True)
            cache.delete(cache_key)
            settings_row.two_factor_enabled = True
            settings_row.save(update_fields=['two_factor_enabled', 'updated_at'])
            messages.success(request, _("Weryfikacja dwustopniowa została włączona."))
            return redirect('two_factor_settings')

        if action == 'disable':
            if settings_row.two_factor_enabled:
                settings_row.two_factor_enabled = False
                settings_row.save(update_fields=['two_factor_enabled', 'updated_at'])
                messages.success(request, _("Weryfikacja dwustopniowa została wyłączona."))
            return redirect('two_factor_settings')

        messages.error(request, _("Nieznana akcja."))
        return redirect('two_factor_settings')


class OTPVerifyView(View):
    """Second step of email-2FA login. Reads otp_pending_user_id from the
    session (set by CaptchaLoginView), accepts the code, and logs the user
    in if it matches."""

    template_name = 'auth/otp_verify.html'
    login_cache_purpose = 'login'

    def get_pending_user(self, request):
        user_id = request.session.get('otp_pending_user_id')
        started = request.session.get('otp_pending_started_at')
        if not user_id or not started:
            return None
        # Stale half-finished login? Force a fresh start.
        if int(time.time()) - int(started) > OTP_SESSION_TIMEOUT_SECONDS:
            self._clear(request)
            return None
        User = get_user_model()
        return User.objects.filter(pk=user_id, is_active=True).first()

    def _clear(self, request):
        for key in ('otp_pending_user_id', 'otp_pending_started_at',
                    'otp_pending_attempts', 'otp_pending_next',
                    'otp_pending_resend_at'):
            request.session.pop(key, None)

    def get(self, request):
        user = self.get_pending_user(request)
        if user is None:
            messages.error(request, _("Twoja sesja logowania wygasła. Zaloguj się ponownie."))
            return redirect('login')
        return render(request, self.template_name, {'form': EmailOTPForm()})

    def post(self, request):
        user = self.get_pending_user(request)
        if user is None:
            messages.error(request, _("Twoja sesja logowania wygasła. Zaloguj się ponownie."))
            return redirect('login')

        form = EmailOTPForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {'form': form})

        cache_key = f"otp:{self.login_cache_purpose}:{user.pk}"
        expected = cache.get(cache_key)
        entered = form.cleaned_data['code']
        attempts = int(request.session.get('otp_pending_attempts', 0)) + 1
        request.session['otp_pending_attempts'] = attempts

        if expected and secrets.compare_digest(expected, entered):
            cache.delete(cache_key)
            next_url = request.session.get('otp_pending_next') or '/'
            self._clear(request)
            auth_login(request, user)
            return redirect(next_url)

        if attempts >= OTP_MAX_ATTEMPTS:
            cache.delete(cache_key)
            self._clear(request)
            messages.error(
                request,
                _("Przekroczono dopuszczalną liczbę prób. Zaloguj się ponownie.")
            )
            return redirect('login')

        remaining = OTP_MAX_ATTEMPTS - attempts
        form.add_error('code', _(
            "Nieprawidłowy lub wygasły kod. Pozostałe próby: %(n)d."
        ) % {'n': remaining})
        return render(request, self.template_name, {'form': form})


class OTPResendCodeView(View):
    """POST-only: re-issue an OTP for the currently parked login attempt,
    throttled to OTP_RESEND_MIN_INTERVAL_SECONDS to limit email spam."""

    login_cache_purpose = 'login'

    def post(self, request):
        verify = OTPVerifyView()
        user = verify.get_pending_user(request)
        if user is None:
            messages.error(request, _("Twoja sesja logowania wygasła. Zaloguj się ponownie."))
            return redirect('login')

        last_resend = request.session.get('otp_pending_resend_at')
        now = int(time.time())
        if last_resend and now - int(last_resend) < OTP_RESEND_MIN_INTERVAL_SECONDS:
            wait = OTP_RESEND_MIN_INTERVAL_SECONDS - (now - int(last_resend))
            messages.warning(
                request,
                _("Kolejny kod możesz wysłać za %(s)d sekund.") % {'s': wait}
            )
            return redirect('otp_verify')

        _issue_otp_for(user, request, purpose=self.login_cache_purpose)
        request.session['otp_pending_resend_at'] = now
        messages.success(request, _("Nowy kod został wysłany na Twój adres e-mail."))
        return redirect('otp_verify')
