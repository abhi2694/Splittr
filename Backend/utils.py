import re
import random
from datetime import datetime, timedelta

ALLOWED_DOMAINS = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "yahoo.in"}

def validate_email(email):
    # Basic email format check
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if not re.match(pattern, email):
        return False
    
    # Check if domain is allowed
    domain = email.split("@")[-1].lower()
    if domain not in ALLOWED_DOMAINS:
        return False

    return True

def validate_password(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False
    return True

def generate_otp():
    return str(random.randint(100000, 999999))

def otp_expiry(minutes):
    return datetime.utcnow() + timedelta(minutes=minutes)
