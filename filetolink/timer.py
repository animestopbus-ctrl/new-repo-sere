import string
import secrets
import datetime

def generate_hash(length=8):
    """Generates a secure, random string for the URL."""
    characters = string.ascii_letters + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def get_expiry_date(hours: int):
    """Calculates the exact UTC datetime when the link should self-destruct."""
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=hours)
