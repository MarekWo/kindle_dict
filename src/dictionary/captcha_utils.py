# kindle_dict\src\dictionary\captcha_utils.py

"""
Utilities for CAPTCHA verification.
"""

import json
import requests
from django.conf import settings
from .models import CaptchaConfiguration

def get_captcha_config():
    """Get the CAPTCHA configuration from the database"""
    try:
        return CaptchaConfiguration.objects.first()
    except:
        return None

def is_captcha_enabled(form_type=None):
    """
    Check if CAPTCHA is enabled globally or for a specific form type
    
    Args:
        form_type (str, optional): The form type to check ('login', 'contact', 'suggest')
        
    Returns:
        bool: True if CAPTCHA is enabled, False otherwise
    """
    config = get_captcha_config()
    
    # If no configuration exists or CAPTCHA is globally disabled, return False
    if not config or not config.is_enabled:
        return False
    
    # If no specific form type is provided, return the global setting
    if not form_type:
        return config.is_enabled
    
    # Check if CAPTCHA is enabled for the specific form type
    if form_type == 'login':
        return config.enable_login
    elif form_type == 'contact':
        return config.enable_contact
    elif form_type == 'suggest':
        return config.enable_suggest
    
    # Default to global setting if form type is not recognized
    return config.is_enabled

def get_captcha_site_key():
    """Get the CAPTCHA site key"""
    config = get_captcha_config()
    if config:
        return config.site_key
    return ''

def get_captcha_provider():
    """Get the CAPTCHA provider"""
    config = get_captcha_config()
    if config:
        return config.provider
    return 'cloudflare'  # Default to Cloudflare

def verify_captcha_response(captcha_response):
    """
    Verify a CAPTCHA response with the appropriate provider
    
    Args:
        captcha_response (str): The CAPTCHA response token from the client
        
    Returns:
        bool: True if verification was successful, False otherwise
    """
    config = get_captcha_config()
    
    if not config or not config.is_enabled or not captcha_response:
        return False
    
    if config.provider == 'cloudflare':
        return verify_cloudflare_turnstile(captcha_response, config.secret_key)
    elif config.provider == 'google':
        return verify_google_recaptcha(captcha_response, config.secret_key)
    
    return False

def verify_cloudflare_turnstile(token, secret_key):
    """
    Verify a Cloudflare Turnstile response
    
    Args:
        token (str): The CAPTCHA response token from the client
        secret_key (str): The secret key for Cloudflare Turnstile
        
    Returns:
        bool: True if verification was successful, False otherwise
    """
    try:
        response = requests.post(
            'https://challenges.cloudflare.com/turnstile/v0/siteverify',
            data={
                'secret': secret_key,
                'response': token,
            }
        )
        
        result = response.json()
        # Nie logujemy tutaj, ponieważ logowanie jest już obsługiwane przez Django
        return result.get('success', False)
    except Exception as e:
        print(f"Error verifying Cloudflare Turnstile: {e}")
        return False

def verify_google_recaptcha(token, secret_key):
    """
    Verify a Google reCAPTCHA response
    
    Args:
        token (str): The CAPTCHA response token from the client
        secret_key (str): The secret key for Google reCAPTCHA
        
    Returns:
        bool: True if verification was successful, False otherwise
    """
    try:
        response = requests.post(
            'https://www.google.com/recaptcha/api/siteverify',
            data={
                'secret': secret_key,
                'response': token,
            }
        )
        
        result = response.json()
        return result.get('success', False)
    except Exception as e:
        print(f"Error verifying Google reCAPTCHA: {e}")
        return False

def get_captcha_context(form_type=None):
    """
    Get the CAPTCHA context for templates
    
    Args:
        form_type (str, optional): The form type ('login', 'contact', 'suggest')
        
    Returns:
        dict: Context dictionary with CAPTCHA information
    """
    enabled = is_captcha_enabled(form_type)
    provider = get_captcha_provider()
    site_key = get_captcha_site_key() if enabled else ''
    
    return {
        'captcha_enabled': enabled,
        'captcha_provider': provider,
        'captcha_site_key': site_key,
    }
