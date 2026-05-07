from datetime import datetime, timedelta
import random
import time

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeSerializer
from passlib.context import CryptContext

from config import (
    IS_PRODUCTION,
    PASSWORD_RESET_SALT,
    SECRET_KEY,
    SESSION_COOKIE_MAX_AGE,
    SESSION_COOKIE_NAME,
)
from models.user import UserModel, VerificationTokenModel
from routes.common import create_session_token, sanitize_text, templates
from services.email_sender import send_password_reset_email, send_verification_email


router = APIRouter(prefix="/auth", tags=["auth"])
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_reset_serializer = URLSafeSerializer(SECRET_KEY, salt=PASSWORD_RESET_SALT)
verify_resend_state: dict[str, dict[str, float | int]] = {}


def _safe_next_path(candidate: str | None) -> str | None:
    if not candidate:
        return None
    if candidate.startswith("/") and not candidate.startswith("//"):
        return candidate
    return None


def _normalize_email(value: str) -> str:
    return (value or "").strip().lower()


def _cooldown_seconds(step: int) -> int:
    return min(20 + max(step, 0) * 10, 60)


def _resend_wait_seconds(email: str) -> int:
    state = verify_resend_state.get(email)
    if not state:
        return 0
    cooldown = _cooldown_seconds(int(state.get("step", 0)))
    elapsed = time.time() - float(state.get("last_sent", 0))
    return max(0, int(cooldown - elapsed))


def _mark_code_sent(email: str, reset: bool = False) -> None:
    if reset:
        verify_resend_state[email] = {"last_sent": time.time(), "step": 0}
        return
    state = verify_resend_state.get(email, {"last_sent": 0.0, "step": 0})
    step = int(state.get("step", 0)) + 1
    verify_resend_state[email] = {"last_sent": time.time(), "step": step}


@router.get("/login")
def login_page(request: Request):
    next_path = _safe_next_path(request.query_params.get("next"))
    success = request.query_params.get("success", "")
    error = request.query_params.get("error", "")
    success_map = {
        "verified": "Email подтвержден. Теперь можно войти.",
        "password_updated": "Пароль обновлен. Войдите с новым паролем.",
    }
    error_map = {
        "bad_token": "Ссылка недействительна или устарела.",
    }
    return templates.TemplateResponse(
        "login.html",
        {
            "request": request,
            "next": next_path,
            "success": success_map.get(success, ""),
            "error": error_map.get(error, ""),
        },
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    next: str = Form(None),
):
    safe_next = _safe_next_path(next)
    user = UserModel.get_by_email(_normalize_email(email))
    if not user or not password_context.verify(password, user["password_hash"]):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Неверный email или пароль", "next": safe_next},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if not user.get("is_verified") and user.get("role") != "global_admin":
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Подтвердите email перед входом. Введите код на странице подтверждения.",
                "next": safe_next,
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    token = create_session_token(user)
    response = RedirectResponse(safe_next or "/", status_code=status.HTTP_303_SEE_OTHER)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=IS_PRODUCTION,
        max_age=SESSION_COOKIE_MAX_AGE,
    )
    return response


@router.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@router.post("/register")
def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    name: str = Form(...),
    role: str = Form("user"),
):
    safe_email = _normalize_email(email)
    safe_name = sanitize_text(name)
    if role not in {"user", "shelter_staff"}:
        role = "user"
    existing_user = UserModel.get_by_email(safe_email)
    if existing_user and existing_user.get("is_verified"):
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Пользователь с таким email уже существует"},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if existing_user and existing_user.get("role") == "global_admin":
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Этот email зарезервирован и недоступен для регистрации."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    if existing_user:
        from database import get_db_cursor

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET password_hash = ?, name = ?, role = ?, shelter_id = NULL, is_verified = 0
                WHERE id = ?
                """,
                (password_context.hash(password), safe_name, role, existing_user["id"]),
            )
        user_id = existing_user["id"]
    else:
        user_id = UserModel.create(
            email=safe_email,
            password_hash=password_context.hash(password),
            name=safe_name,
            role=role,
        )
    code = f"{random.randint(0, 999999):06d}"
    VerificationTokenModel.mark_all_used(user_id, "email_verify")
    VerificationTokenModel.create(
        user_id=user_id,
        token=code,
        token_type="email_verify",
        expires_at=datetime.now() + timedelta(hours=24),
    )

    try:
        send_verification_email(safe_email, code)
    except Exception:
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "error": "Аккаунт создан, но письмо не отправилось. Обратитесь к администратору.",
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    _mark_code_sent(safe_email, reset=True)

    return templates.TemplateResponse(
        "verify_email.html",
        {
            "request": request,
            "email": safe_email,
            "success": "Аккаунт создан. Введите 6-значный код из письма.",
            "retry_after": _cooldown_seconds(0),
        },
    )


@router.get("/verify-email")
def verify_email_page(request: Request, email: str = ""):
    safe_email = _normalize_email(email)
    return templates.TemplateResponse(
        "verify_email.html",
        {"request": request, "email": safe_email, "retry_after": _resend_wait_seconds(safe_email)},
    )


@router.post("/verify-email")
def verify_email(request: Request, email: str = Form(...), code: str = Form(...)):
    safe_email = _normalize_email(email)
    user = UserModel.get_by_email(safe_email)
    if not user:
        return templates.TemplateResponse(
            "verify_email.html",
            {"request": request, "email": safe_email, "error": "Пользователь с таким email не найден."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    normalized_code = "".join(ch for ch in (code or "") if ch.isdigit())[:6]
    if len(normalized_code) != 6:
        return templates.TemplateResponse(
            "verify_email.html",
            {"request": request, "email": safe_email, "error": "Код должен содержать 6 цифр."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    token_data = VerificationTokenModel.get_valid_for_user(user["id"], normalized_code, "email_verify")
    if not token_data:
        latest = VerificationTokenModel.get_latest_valid_for_user(user["id"], "email_verify")
        if latest:
            latest_normalized = "".join(ch for ch in str(latest["token"]) if ch.isdigit())[:6]
            if latest_normalized == normalized_code:
                token_data = latest
    if not token_data:
        return templates.TemplateResponse(
            "verify_email.html",
            {
                "request": request,
                "email": safe_email,
                "error": "Неверный или просроченный код.",
                "retry_after": _resend_wait_seconds(safe_email),
            },
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    UserModel.verify_email(user["id"])
    VerificationTokenModel.mark_used(token_data["id"])
    VerificationTokenModel.mark_all_used(user["id"], "email_verify")
    verify_resend_state.pop(safe_email, None)
    return RedirectResponse("/auth/login?success=verified", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/verify-email/resend")
def resend_verify_code(request: Request, email: str = Form(...)):
    safe_email = _normalize_email(email)
    user = UserModel.get_by_email(safe_email)
    if not user:
        return templates.TemplateResponse(
            "verify_email.html",
            {"request": request, "email": safe_email, "error": "Пользователь с таким email не найден."},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    if user.get("is_verified"):
        return RedirectResponse("/auth/login?success=verified", status_code=status.HTTP_303_SEE_OTHER)

    wait = _resend_wait_seconds(safe_email)
    if wait > 0:
        return templates.TemplateResponse(
            "verify_email.html",
            {
                "request": request,
                "email": safe_email,
                "error": f"Подождите {wait} сек. перед повторной отправкой кода.",
                "retry_after": wait,
            },
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    code = f"{random.randint(0, 999999):06d}"
    VerificationTokenModel.mark_all_used(user["id"], "email_verify")
    VerificationTokenModel.create(
        user_id=user["id"],
        token=code,
        token_type="email_verify",
        expires_at=datetime.now() + timedelta(hours=24),
    )
    try:
        send_verification_email(safe_email, code)
    except Exception:
        return templates.TemplateResponse(
            "verify_email.html",
            {
                "request": request,
                "email": safe_email,
                "error": "Не удалось отправить код. Попробуйте позже.",
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    _mark_code_sent(safe_email, reset=False)
    return templates.TemplateResponse(
        "verify_email.html",
        {
            "request": request,
            "email": safe_email,
            "success": "Новый код отправлен на почту.",
            "retry_after": _cooldown_seconds(int(verify_resend_state[safe_email]["step"])),
        },
    )


@router.get("/restore-password")
def restore_password_page(request: Request):
    return templates.TemplateResponse("restore_password.html", {"request": request})


@router.post("/restore-password")
def restore_password_request(request: Request, email: str = Form(...)):
    user = UserModel.get_by_email(email)
    if user:
        token = password_reset_serializer.dumps({"user_id": user["id"]})
        VerificationTokenModel.create(
            user_id=user["id"],
            token=token,
            token_type="password_reset",
            expires_at=datetime.now() + timedelta(hours=2),
        )
        try:
            send_password_reset_email(user["email"], token)
        except Exception:
            return templates.TemplateResponse(
                "restore_password.html",
                {
                    "request": request,
                    "error": "Не удалось отправить письмо. Попробуйте позже.",
                },
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
    return templates.TemplateResponse(
        "restore_password.html",
        {
            "request": request,
            "success": "Если email существует, мы отправили ссылку для смены пароля.",
        },
    )


@router.get("/reset-password")
def reset_password_page(request: Request, token: str):
    token_data = VerificationTokenModel.get_valid(token, "password_reset")
    if not token_data:
        return RedirectResponse("/auth/restore-password?error=bad_token", status_code=status.HTTP_303_SEE_OTHER)
    return templates.TemplateResponse("restore_password.html", {"request": request, "token": token})


@router.post("/reset-password")
def reset_password(token: str = Form(...), password: str = Form(...)):
    token_data = VerificationTokenModel.get_valid(token, "password_reset")
    if not token_data:
        return RedirectResponse("/auth/restore-password?error=bad_token", status_code=status.HTTP_303_SEE_OTHER)
    UserModel.update_password(token_data["user_id"], password_context.hash(password))
    VerificationTokenModel.mark_used(token_data["id"])
    return RedirectResponse("/auth/login?success=password_updated", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/logout")
def logout():
    response = RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    response.delete_cookie(SESSION_COOKIE_NAME)
    return response
