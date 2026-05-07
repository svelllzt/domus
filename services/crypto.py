import base64
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from config import SECRET_KEY, SMTP_ENCRYPTION_KEY


def _build_fernet() -> Fernet:
    source = SMTP_ENCRYPTION_KEY or f"fallback::{SECRET_KEY}"
    digest = hashlib.sha256(source.encode("utf-8")).digest()
    key = base64.urlsafe_b64encode(digest)
    return Fernet(key)


def encrypt_value(value: str) -> str:
    if not value:
        return ""
    fernet = _build_fernet()
    return fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str) -> str:
    if not value:
        return ""
    fernet = _build_fernet()
    try:
        return fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""
