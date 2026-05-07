from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from models.application import ShelterRegistrationRequestModel
from models.shelter import ShelterModel
from models.system_settings import SystemSettingsModel
from models.user import UserModel
from services.crypto import encrypt_value
from services.email_sender import send_test_email, smtp_status
from routes.common import get_current_user, has_role, sanitize_text, templates


router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard")
def admin_dashboard(request: Request):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    requests = ShelterRegistrationRequestModel.list_all()
    shelters = ShelterModel.list_all()
    users = UserModel.list_recent(limit=50)
    smtp_result = request.query_params.get("smtp_result", "")
    smtp_error = request.query_params.get("smtp_error", "")
    return templates.TemplateResponse(
        "admin_dashboard.html",
        {
            "request": request,
            "user": user,
            "requests": requests,
            "shelters": shelters,
            "users": users,
            "smtp": smtp_status(),
            "smtp_result": smtp_result,
            "smtp_error": smtp_error,
        },
    )


@router.post("/registration-request/{request_id}/approve")
def approve_shelter_request(request: Request, request_id: int, admin_comment: str = Form("")):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    request_data = ShelterRegistrationRequestModel.get_by_id(request_id)
    if not request_data or request_data["status"] != "new":
        return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    shelter_id = ShelterModel.create(
        name=request_data["shelter_name"],
        city=request_data["shelter_city"],
        address=request_data["shelter_address"],
        phone=request_data["shelter_phone"],
        description=request_data["shelter_description"],
        is_approved=1,
    )
    UserModel.set_role_and_shelter(request_data["user_id"], "shelter_admin", shelter_id)
    ShelterRegistrationRequestModel.set_status(request_id, "approved", sanitize_text(admin_comment))
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/registration-request/{request_id}/reject")
def reject_shelter_request(request: Request, request_id: int, admin_comment: str = Form(...)):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    ShelterRegistrationRequestModel.set_status(request_id, "rejected", sanitize_text(admin_comment))
    return RedirectResponse("/admin/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/smtp-settings")
def save_smtp_settings(
    request: Request,
    host: str = Form(...),
    port: int = Form(587),
    username: str = Form(""),
    password: str = Form(""),
    from_email: str = Form(...),
    from_name: str = Form(""),
    security: str = Form("starttls"),
):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    current = SystemSettingsModel.get_many(["smtp_password_encrypted"])
    encrypted_password = current.get("smtp_password_encrypted", "")
    if password.strip():
        encrypted_password = encrypt_value(password.strip())

    SystemSettingsModel.set_many(
        {
            "smtp_host": sanitize_text(host),
            "smtp_port": str(port),
            "smtp_username": sanitize_text(username),
            "smtp_password_encrypted": encrypted_password,
            "smtp_from_email": sanitize_text(from_email),
            "smtp_from_name": sanitize_text(from_name),
            "smtp_security": sanitize_text(security or "starttls"),
        }
    )
    return RedirectResponse("/admin/dashboard?smtp_result=saved", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/smtp-settings/test")
def test_smtp_settings(request: Request, test_email: str = Form(...)):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    try:
        send_test_email(sanitize_text(test_email))
    except Exception:
        return RedirectResponse("/admin/dashboard?smtp_error=send_failed", status_code=status.HTTP_303_SEE_OTHER)
    return RedirectResponse("/admin/dashboard?smtp_result=test_sent", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/smtp-settings/clear")
def clear_smtp_settings(request: Request):
    user = get_current_user(request)
    if not has_role(user, {"global_admin"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    SystemSettingsModel.set_many(
        {
            "smtp_host": "",
            "smtp_port": "",
            "smtp_username": "",
            "smtp_password_encrypted": "",
            "smtp_from_email": "",
            "smtp_from_name": "",
            "smtp_security": "starttls",
        }
    )
    return RedirectResponse("/admin/dashboard?smtp_result=cleared", status_code=status.HTTP_303_SEE_OTHER)
