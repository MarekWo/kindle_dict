# kindle_dict\src\dictionary\auth_views.py

"""
Authentication views with CAPTCHA support.
"""

from django.contrib.auth.views import LoginView
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _
from django import forms
from django.shortcuts import render, redirect
from django.contrib import messages

from .captcha_utils import verify_captcha_response, get_captcha_context, is_captcha_enabled

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
