from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext

from models.application import AdoptionApplicationModel
from models.favorite import FavoriteModel
from models.user import UserModel
from routes.common import get_current_user, has_role, templates


router = APIRouter(prefix="/user", tags=["user"])
password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@router.get("/dashboard")
def user_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    if not has_role(user, {"user"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    favorites = FavoriteModel.list_for_user(user["id"])
    for animal in favorites:
        animal["is_favorite"] = True
    applications = AdoptionApplicationModel.list_for_user(user["id"])
    password_result = request.query_params.get("password_result", "")
    return templates.TemplateResponse(
        "user_dashboard.html",
        {
            "request": request,
            "user": user,
            "favorites": favorites,
            "applications": applications,
            "password_result": password_result,
        },
    )


@router.post("/change-password")
def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
):
    user = get_current_user(request)
    if not has_role(user, {"user"}):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    if len(new_password) < 8:
        return RedirectResponse(
            "/user/dashboard?password_result=too_short",
            status_code=status.HTTP_303_SEE_OTHER,
        )
    if not password_context.verify(current_password, user["password_hash"]):
        return RedirectResponse(
            "/user/dashboard?password_result=wrong_current",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    UserModel.update_password(user["id"], password_context.hash(new_password))
    return RedirectResponse("/user/dashboard?password_result=updated", status_code=status.HTTP_303_SEE_OTHER)
