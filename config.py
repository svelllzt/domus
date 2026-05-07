import os
from pathlib import Path
import secrets


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "pets.db"
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
UPLOADS_DIR = STATIC_DIR / "uploads"

SECRET_KEY = os.getenv("PETS_SECRET_KEY", "" + secrets.token_hex(8))
APP_ENV = (os.getenv("PETS_ENV", "production") or "production").lower()
IS_PRODUCTION = APP_ENV == "production"
APP_BASE_URL = os.getenv("PETS_APP_BASE_URL", "http://").rstrip("/")
SMTP_ENCRYPTION_KEY = os.getenv("PETS_SMTP_ENCRYPTION_KEY", "")

SESSION_COOKIE_NAME = "pets_session"
SESSION_COOKIE_MAX_AGE = int(os.getenv("PETS_SESSION_MAX_AGE", str(7 * 24 * 60 * 60)))
TOKEN_SALT = ""
EMAIL_TOKEN_SALT = ""
PASSWORD_RESET_SALT = ""
GLOBAL_ADMIN_EMAIL = os.getenv("PETS_GLOBAL_ADMIN_EMAIL", "admin@domus.local").strip().lower()
GLOBAL_ADMIN_PASSWORD = os.getenv("PETS_GLOBAL_ADMIN_PASSWORD", "DomusAdmin")

MAX_UPLOAD_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

ITEMS_PER_PAGE = 12
