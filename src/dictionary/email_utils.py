"""
Email utilities for the Dictionary app.
"""

import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import SMTPConfiguration

logger = logging.getLogger(__name__)

def get_smtp_config():
    """Get the SMTP configuration from the database"""
    try:
        return SMTPConfiguration.objects.first()
    except Exception as e:
        logger.error(f"Error getting SMTP configuration: {e}")
        return None

def send_email(to_email, subject, html_content, text_content=None, smtp_config=None, headers=None):
    """
    Send an email using the configured SMTP server.
    
    Args:
        to_email (str): Recipient email address
        subject (str): Email subject
        html_content (str): HTML content of the email
        text_content (str, optional): Plain text content of the email
        smtp_config (SMTPConfiguration, optional): SMTP configuration to use
        headers (dict, optional): Additional headers to add to the email (e.g. Reply-To)
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not smtp_config:
        smtp_config = get_smtp_config()
    
    if not smtp_config:
        logger.error("No SMTP configuration found")
        return False
    
    # Przygotuj treść tekstową
    if not text_content:
        # Very simple HTML to text conversion
        text_content = html_content.replace('<br>', '\n').replace('<p>', '\n').replace('</p>', '\n')
        text_content = ''.join([i if ord(i) < 128 else ' ' for i in text_content])
    
    # Użyjmy najprostszego możliwego podejścia
    import smtplib
    from email.message import EmailMessage
    
    # Utwórz wiadomość
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = f"{smtp_config.from_name} <{smtp_config.from_email}>"
    msg['To'] = to_email
    
    # Dodaj dodatkowe nagłówki, jeśli są
    if headers:
        for header_name, header_value in headers.items():
            msg[header_name] = header_value
    
    # Ustaw treść
    msg.set_content(text_content)
    msg.add_alternative(html_content, subtype='html')
    
    try:
        # Bezpośrednie użycie smtplib
        import smtplib
        
        # Wybierz odpowiedni typ połączenia
        if smtp_config.encryption == 'ssl':
            server = smtplib.SMTP_SSL(smtp_config.host, smtp_config.port)
        else:
            server = smtplib.SMTP(smtp_config.host, smtp_config.port)
            
            # Użyj TLS jeśli skonfigurowano
            if smtp_config.encryption == 'tls':
                server.starttls()
        
        # Logowanie jeśli wymagane
        if smtp_config.authentication:
            server.login(smtp_config.username, smtp_config.password)
        
        # Wyślij wiadomość
        server.send_message(msg)
        server.quit()
        
        # Logujemy wysłanie e-maila
        logger.info(f"Email sent to {to_email}: {subject}")
        return True
    
    except Exception as e:
        logger.error(f"Error sending email to {to_email}: {e}")
        return False

def send_dictionary_completion_email(dictionary):
    """
    Send an email notification to the dictionary creator when the dictionary is completed.
    
    Args:
        dictionary: Dictionary object that was completed
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    from django.contrib.auth import get_user_model
    from django.contrib.auth.models import User
    
    # Pobierz informacje o twórcy słownika z modelu Dictionary
    creator_name = dictionary.creator_name
    logger.info(f"Sending completion notification for dictionary creator: {creator_name}")
    
    # Spróbuj znaleźć użytkownika na podstawie różnych kryteriów
    matching_users = []
    
    # 1. Najpierw spróbuj znaleźć użytkownika, którego pełne imię i nazwisko pasuje do creator_name
    for user in User.objects.all():
        full_name = f"{user.first_name} {user.last_name}".strip()
        if full_name and full_name == creator_name:
            matching_users.append(user)
            logger.info(f"Found user by full name: {user.username}")
            break
    
    # 2. Jeśli nie znaleziono, spróbuj znaleźć użytkownika po nazwie użytkownika
    if not matching_users:
        # Sprawdź, czy creator_name pasuje do nazwy użytkownika
        matching_users = User.objects.filter(username=creator_name)
        if matching_users:
            logger.info(f"Found user by username: {matching_users[0].username}")
    
    # 3. Jeśli nadal nie znaleziono, spróbuj znaleźć użytkownika, który ma podobną nazwę użytkownika
    if not matching_users:
        # Podziel creator_name na części i spróbuj znaleźć użytkownika, który ma podobną nazwę użytkownika
        name_parts = creator_name.split()
        for part in name_parts:
            if len(part) > 2:  # Ignoruj krótkie części
                users = User.objects.filter(username__icontains=part)
                if users:
                    matching_users = users
                    logger.info(f"Found user by partial username match: {users[0].username}")
                    break
    
    # 4. Jeśli nadal nie znaleziono, spróbuj znaleźć użytkownika po adresie e-mail
    if not matching_users:
        # Sprawdź, czy creator_name wygląda jak adres e-mail
        if '@' in creator_name:
            matching_users = User.objects.filter(email=creator_name)
            if matching_users:
                logger.info(f"Found user by email: {matching_users[0].email}")
    
    # 5. Jeśli nadal nie znaleziono, po prostu weź pierwszego administratora
    if not matching_users:
        matching_users = User.objects.filter(is_superuser=True)
        if matching_users:
            logger.info(f"Using superuser as fallback: {matching_users[0].username}")
    
    if not matching_users:
        logger.warning(f"Could not find any user for dictionary creator: {creator_name}")
        return False
    
    # Get the first matching user's email
    creator_email = matching_users[0].email
    
    if not creator_email:
        logger.warning(f"User found but has no email: {matching_users[0].username}")
        return False
    
    # Prepare email content
    subject = str(_("Twój słownik został utworzony"))
    html_content = """
    <html>
    <body>
        <h2>Słownik został utworzony</h2>
        <p>Witaj {creator_name},</p>
        <p>Twój słownik <strong>{dictionary_name}</strong> został pomyślnie utworzony.</p>
        <p>Możesz go pobrać z naszej strony:</p>
        <p><a href="{site_url}/dictionary/{dictionary_id}/">Pobierz słownik</a></p>
        <br>
        <p>Pozdrawiamy,<br>
        Zespół Kindle Dictionary Creator</p>
    </body>
    </html>
    """.format(
        creator_name=dictionary.creator_name,
        dictionary_name=dictionary.name,
        dictionary_id=dictionary.id,
        site_url=settings.SITE_URL
    )
    
    # Send the email to the creator
    success = send_email(creator_email, subject, html_content)
    
    if success:
        logger.info(f"Completion notification sent to {creator_email} for dictionary: {dictionary.id}")
    else:
        logger.error(f"Failed to send completion notification to {creator_email} for dictionary: {dictionary.id}")
    
    # If there's an additional notification email, send to that as well
    if dictionary.notification_email:
        additional_success = send_email(dictionary.notification_email, subject, html_content)
        if additional_success:
            logger.info(f"Additional completion notification sent to {dictionary.notification_email} for dictionary: {dictionary.id}")
        else:
            logger.error(f"Failed to send additional completion notification to {dictionary.notification_email} for dictionary: {dictionary.id}")
        
        # Return True only if both emails were sent successfully
        return success and additional_success
    
    return success

def send_test_email(to_email, smtp_config=None):
    """
    Send a test email to verify SMTP configuration.
    
    Args:
        to_email (str): Email address to send the test to
        smtp_config (SMTPConfiguration, optional): SMTP configuration to use
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Konwertuj gettext_lazy na string
    subject = str(_("Test wiadomości z Kindle Dictionary Creator"))
    html_content = """
    <html>
    <body>
        <h2>Test konfiguracji SMTP</h2>
        <p>To jest testowa wiadomość z aplikacji Kindle Dictionary Creator.</p>
        <p>Jeśli otrzymałeś tę wiadomość, oznacza to, że konfiguracja SMTP działa poprawnie.</p>
        <p>Adres strony: <a href="{site_url}">{site_url}</a></p>
        <br>
        <p>Pozdrawiamy,<br>
        Zespół Kindle Dictionary Creator</p>
    </body>
    </html>
    """.format(site_url=settings.SITE_URL)
    
    return send_email(to_email, subject, html_content, smtp_config=smtp_config)

def get_admin_users():
    """
    Get all users who are administrators (superusers or in Dictionary Admin group).
    
    Returns:
        list: List of User objects
    """
    User = get_user_model()
    
    # Get all superusers
    superusers = User.objects.filter(is_superuser=True)
    
    # Get all users in Dictionary Admin group
    try:
        admin_group = Group.objects.get(name='Dictionary Admin')
        admin_users = admin_group.user_set.all()
    except Group.DoesNotExist:
        admin_users = User.objects.none()
    
    # Combine and remove duplicates
    admin_users = (superusers | admin_users).distinct()
    
    return admin_users

def get_dictionary_creator_users():
    """
    Get all users who can create dictionaries (superusers, Dictionary Admin, or Dictionary Creator).
    
    Returns:
        list: List of User objects
    """
    User = get_user_model()
    
    # Get all superusers
    superusers = User.objects.filter(is_superuser=True)
    
    # Get all users in Dictionary Admin group
    try:
        admin_group = Group.objects.get(name='Dictionary Admin')
        admin_users = admin_group.user_set.all()
    except Group.DoesNotExist:
        admin_users = User.objects.none()
    
    # Get all users in Dictionary Creator group
    try:
        creator_group = Group.objects.get(name='Dictionary Creator')
        creator_users = creator_group.user_set.all()
    except Group.DoesNotExist:
        creator_users = User.objects.none()
    
    # Combine and remove duplicates
    all_users = (superusers | admin_users | creator_users).distinct()
    
    return all_users

def send_contact_message_notification(contact_message):
    """
    Send a notification to administrators about a new contact message.
    
    Args:
        contact_message: ContactMessage object that was created
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Get all admin users
    admin_users = get_admin_users()
    
    if not admin_users:
        logger.warning("No admin users found to notify about contact message")
        return False
    
    # Prepare email content
    subject = str(_("Nowa wiadomość kontaktowa"))
    
    # Format the message with line breaks for HTML
    message_html = contact_message.message.replace('\n', '<br>')
    
    html_content = """
    <html>
    <body>
        <h2>Nowa wiadomość kontaktowa</h2>
        <p>Otrzymałeś nową wiadomość kontaktową:</p>
        
        <p><strong>Od:</strong> {name}</p>
        <p><strong>E-mail:</strong> {email}</p>
        <p><strong>Data:</strong> {date}</p>
        <p><strong>Wiadomość:</strong></p>
        <div style="padding: 10px; border-left: 4px solid #ccc; margin-left: 20px;">
            {message}
        </div>
        
        <p>Możesz zobaczyć wszystkie wiadomości w <a href="{site_url}/admin/dictionary/contactmessage/">panelu administracyjnym</a>.</p>
        <br>
        <p>Pozdrawiamy,<br>
        System Kindle Dictionary Creator</p>
    </body>
    </html>
    """.format(
        name=contact_message.name or "Anonimowy",
        email=contact_message.email or "Nie podano",
        date=contact_message.created_at.strftime("%Y-%m-%d %H:%M"),
        message=message_html,
        site_url=settings.SITE_URL
    )
    
    # Set up reply-to if email is provided
    headers = {}
    if contact_message.email:
        if contact_message.name:
            headers['Reply-To'] = f"{contact_message.name} <{contact_message.email}>"
        else:
            headers['Reply-To'] = contact_message.email
    
    # Send to all admin users
    success = True
    for user in admin_users:
        if user.email:
            result = send_email(user.email, subject, html_content, headers=headers)
            if not result:
                logger.error(f"Failed to send contact message notification to {user.email}")
                success = False
    
    return success

def send_task_notification(task, status_change=False):
    """
    Send a notification to administrators about a new task or task status change.
    
    Args:
        task: Task object that was created or updated
        status_change: Whether this is a notification about a status change
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    # Get all users who can create dictionaries
    users = get_dictionary_creator_users()
    
    if not users:
        logger.warning("No users found to notify about task")
        return False
    
    # Prepare email content
    if status_change:
        subject = str(_("Zmiana statusu zadania: {0}")).format(task.get_status_display())
    else:
        subject = str(_("Nowe zadanie: {0}")).format(task.title)
    
    # Format the description with line breaks for HTML
    description_html = task.description.replace('\n', '<br>') if task.description else ""
    
    html_content = """
    <html>
    <body>
        <h2>{subject}</h2>
        <p><strong>Tytuł:</strong> {title}</p>
        <p><strong>Typ zadania:</strong> {task_type}</p>
        <p><strong>Status:</strong> {status}</p>
        <p><strong>Data utworzenia:</strong> {created_at}</p>
        
        {description_section}
        
        <p>Możesz zobaczyć wszystkie zadania w <a href="{site_url}/dictionary/tasks/">panelu zadań</a>.</p>
        <br>
        <p>Pozdrawiamy,<br>
        System Kindle Dictionary Creator</p>
    </body>
    </html>
    """.format(
        subject=subject,
        title=task.title,
        task_type=task.get_task_type_display(),
        status=task.get_status_display(),
        created_at=task.created_at.strftime("%Y-%m-%d %H:%M"),
        description_section=f"""
        <p><strong>Opis:</strong></p>
        <div style="padding: 10px; border-left: 4px solid #ccc; margin-left: 20px;">
            {description_html}
        </div>
        """ if description_html else "",
        site_url=settings.SITE_URL
    )
    
    # Send to all users
    success = True
    for user in users:
        if user.email:
            result = send_email(user.email, subject, html_content)
            if not result:
                logger.error(f"Failed to send task notification to {user.email}")
                success = False
    
    return success

def send_task_status_notification_to_submitter(task):
    """
    Send a notification to the task submitter about a status change.
    
    Args:
        task: Task object that was updated
        
    Returns:
        bool: True if email was sent successfully, False otherwise
    """
    if not task.email:
        logger.info(f"No email address for task submitter: {task.id}")
        return False
    
    # Prepare email content
    subject = str(_("Aktualizacja statusu Twojego zgłoszenia"))
    
    html_content = """
    <html>
    <body>
        <h2>Aktualizacja statusu Twojego zgłoszenia</h2>
        <p>Witaj,</p>
        <p>Status Twojego zgłoszenia <strong>"{title}"</strong> został zmieniony na <strong>{status}</strong>.</p>
        
        {additional_info}
        
        <p>Dziękujemy za Twoje zgłoszenie!</p>
        <br>
        <p>Pozdrawiamy,<br>
        Zespół Kindle Dictionary Creator</p>
    </body>
    </html>
    """.format(
        title=task.title,
        status=task.get_status_display(),
        additional_info=get_status_additional_info(task)
    )
    
    # Send to submitter
    success = send_email(task.email, subject, html_content)
    
    if success:
        logger.info(f"Status notification sent to {task.email} for task: {task.id}")
    else:
        logger.error(f"Failed to send status notification to {task.email} for task: {task.id}")
    
    return success

def get_status_additional_info(task):
    """
    Get additional information based on task status.
    
    Args:
        task: Task object
        
    Returns:
        str: HTML content with additional information
    """
    if task.status == 'rejected':
        rejection_reason = task.rejection_reason if task.rejection_reason else "Nie podano powodu odrzucenia."
        return f"""
        <p>Niestety, Twoje zgłoszenie zostało odrzucone.</p>
        <p><strong>Powód odrzucenia:</strong></p>
        <div style="padding: 10px; border-left: 4px solid #ccc; margin-left: 20px;">
            {rejection_reason}
        </div>
        """
    elif task.status == 'accepted':
        return """
        <p>Twoje zgłoszenie zostało zaakceptowane i oczekuje na realizację. 
        Zostaniesz powiadomiony, gdy słownik zostanie utworzony.</p>
        """
    elif task.status == 'completed':
        if task.related_dictionary:
            return """
            <p>Twoje zgłoszenie zostało zrealizowane! Słownik jest już dostępny do pobrania.</p>
            <p>Możesz pobrać słownik z naszej strony: 
            <a href="{site_url}/dictionary/{dictionary_id}/">Pobierz słownik</a></p>
            """.format(
                site_url=settings.SITE_URL,
                dictionary_id=task.related_dictionary.id
            )
        else:
            return """
            <p>Twoje zgłoszenie zostało zrealizowane! Słownik powinien być już dostępny do pobrania na naszej stronie.</p>
            """
    else:
        return ""
