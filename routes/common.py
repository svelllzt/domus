from datetime import datetime, timedelta
from typing import Any

from fastapi import Request
from fastapi.templating import Jinja2Templates
from itsdangerous import BadSignature, URLSafeSerializer
from markupsafe import escape

from config import SECRET_KEY, SESSION_COOKIE_NAME, TEMPLATES_DIR, TOKEN_SALT
from models.user import UserModel


session_serializer = URLSafeSerializer(SECRET_KEY, salt=TOKEN_SALT)
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def sanitize_text(value: str | None) -> str:
    if not value:
        return ""
    return str(escape(value.strip()))


def create_session_token(user: dict[str, Any]) -> str:
    expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
    payload = {
        "user_id": user["id"],
        "role": user["role"],
        "shelter_id": user.get("shelter_id"),
        "exp": expires_at,
    }
    return session_serializer.dumps(payload)


def decode_session_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        data = session_serializer.loads(token)
        if datetime.fromisoformat(data["exp"]) < datetime.utcnow():
            return None
        return data
    except (BadSignature, KeyError, ValueError):
        return None


def get_current_user(request: Request) -> dict[str, Any] | None:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    payload = decode_session_token(token)
    if not payload:
        return None
    return UserModel.get_by_id(payload["user_id"])


def has_role(user: dict[str, Any] | None, allowed_roles: set[str]) -> bool:
    return bool(user and user.get("role") in allowed_roles)


def parse_search_filters(request: Request) -> dict[str, Any]:
    """Парсинг query-параметров поиска (в т.ч. списки через запятую для мультивыбора)."""
    qp = request.query_params

    def csv(key: str) -> list[str]:
        raw = qp.get(key, "") or ""
        return [part.strip() for part in raw.split(",") if part.strip()]

    return {
        "species": csv("species"),
        "sex": csv("sex"),
        "size": csv("size"),
        "city": csv("city"),
        "age_ranges": csv("age"),
        "status": (qp.get("status", "") or "available").strip(),
        "query": (qp.get("query", "") or "").strip(),
    }
