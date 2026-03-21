import os
from datetime import timedelta

class Config:
    SQLALCHEMY_DATABASE_URI = "sqlite:///users.db"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    OTP_EXPIRY_MINUTES = 10
    MAX_FAILED_ATTEMPTS = 5
    LOCK_TIME_MINUTES = 10
    SECRET_KEY = "dev-secret"
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = False
    # Email configuration (Gmail example)
    MAIL_SERVER = "smtp.gmail.com"
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = "abhi2694@gmail.com"
    MAIL_PASSWORD = "rhgk vntn fcfn kyai"
