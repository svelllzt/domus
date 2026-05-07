import smtplib
from email.message import EmailMessage

from config import APP_BASE_URL
from models.system_settings import SystemSettingsModel
from services.crypto import decrypt_value


SMTP_KEYS = [
    "smtp_host",
    "smtp_port",
    "smtp_username",
    "smtp_password_encrypted",
    "smtp_from_email",
    "smtp_from_name",
    "smtp_security",
]


def _smtp_settings() -> dict[str, str]:
    data = SystemSettingsModel.get_many(SMTP_KEYS)
    return {
        "host": data.get("smtp_host", "").strip(),
        "port": data.get("smtp_port", "587").strip(),
        "username": data.get("smtp_username", "").strip(),
        "password": decrypt_value(data.get("smtp_password_encrypted", "")),
        "from_email": data.get("smtp_from_email", "").strip(),
        "from_name": data.get("smtp_from_name", "").strip(),
        "security": (data.get("smtp_security", "starttls") or "starttls").lower(),
    }


def smtp_status() -> dict[str, str | bool]:
    settings = _smtp_settings()
    return {
        "configured": bool(settings["host"] and settings["from_email"]),
        "host": settings["host"],
        "port": settings["port"],
        "username": settings["username"],
        "from_email": settings["from_email"],
        "from_name": settings["from_name"],
        "security": settings["security"],
    }


def _make_message(to_email: str, subject: str, body: str) -> EmailMessage:
    settings = _smtp_settings()
    msg = EmailMessage()
    from_label = settings["from_name"] or "Pets"
    msg["From"] = f"{from_label} <{settings['from_email']}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)
    return msg


def _deliver(message: EmailMessage) -> None:
    settings = _smtp_settings()
    if not settings["host"] or not settings["from_email"]:
        raise RuntimeError("SMTP не настроен")

    port = int(settings["port"] or 587)
    security = settings["security"]
    username = settings["username"]
    password = settings["password"]

    if security == "ssl":
        with smtplib.SMTP_SSL(settings["host"], port, timeout=15) as smtp:
            if username:
                smtp.login(username, password)
            smtp.send_message(message)
        return

    with smtplib.SMTP(settings["host"], port, timeout=15) as smtp:
        if security == "starttls":
            smtp.starttls()
        if username:
            smtp.login(username, password)
        smtp.send_message(message)


def send_verification_email(to_email: str, code: str) -> None:
    body = (
        "Подтвердите email для доступа к аккаунту.\n\n"
        f"Код подтверждения: {code}\n\n"
        "Код действует 24 часа. Если вы не регистрировались, просто проигнорируйте письмо."
    )
    _deliver(_make_message(to_email, "Подтверждение email", body))


def send_password_reset_email(to_email: str, token: str) -> None:
    reset_url = f"{APP_BASE_URL}/auth/reset-password?token={token}"
    body = (
        "Мы получили запрос на смену пароля.\n\n"
        f"Ссылка для сброса: {reset_url}\n\n"
        "Если это были не вы, можно ничего не делать."
    )
    _deliver(_make_message(to_email, "Сброс пароля", body))


def send_test_email(to_email: str) -> None:
    body = (
        "SMTP настроен корректно.\n\n"
        "Это тестовое письмо, отправленное из глобальной админки."
    )
    _deliver(_make_message(to_email, "Тест SMTP", body))
