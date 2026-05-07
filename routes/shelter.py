import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, Request, UploadFile, status
from fastapi.responses import RedirectResponse

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE_BYTES, UPLOADS_DIR
from models.animal import AnimalModel
from models.application import AdoptionApplicationModel, ShelterRegistrationRequestModel
from routes.common import get_current_user, has_role, sanitize_text, templates


router = APIRouter(prefix="/shelter", tags=["shelter"])
ALLOWED_SPECIES = {"cat", "dog"}
ALLOWED_SEX = {"unknown", "male", "female"}
ALLOWED_SIZE = {"small", "medium", "large"}
ALLOWED_ANIMAL_STATUS = {"available", "processing", "adopted"}
MAX_PHOTOS_PER_ANIMAL = 5


def _save_photo(photo: UploadFile) -> str:
    file_ext = Path(photo.filename or "").suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Недопустимый формат файла")

    content = photo.file.read()
    if len(content) > MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("Файл больше 5 МБ")

    filename = f"{uuid.uuid4().hex}{file_ext}"
    file_path = UPLOADS_DIR / filename
    with open(file_path, "wb") as output_file:
        output_file.write(content)
    return filename


def _normalize_choice(value: str, allowed: set[str], fallback: str) -> str:
    clean_value = sanitize_text(value)
    return clean_value if clean_value in allowed else fallback


def _attach_uploaded_photos(animal_id: int, photos: list[UploadFile]) -> None:
    if not photos:
        return
    existing_count = AnimalModel.count_photos(animal_id)
    slots_left = max(MAX_PHOTOS_PER_ANIMAL - existing_count, 0)
    if slots_left == 0:
        return

    uploaded = 0
    for photo in photos:
        if uploaded >= slots_left:
            break
        if not photo or not photo.filename:
            continue
        try:
            filename = _save_photo(photo)
        except ValueError:
            continue
        AnimalModel.add_photo(animal_id, filename, is_main=(existing_count == 0 and uploaded == 0))
        uploaded += 1


@router.get("/dashboard")
def shelter_dashboard(request: Request):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    if has_role(user, {"shelter_staff"}) and not user.get("shelter_id"):
        requests = ShelterRegistrationRequestModel.get_for_user(user["id"])
        return templates.TemplateResponse(
            "shelter_registration_request.html",
            {"request": request, "user": user, "requests": requests},
        )
    if not has_role(user, {"shelter_admin", "shelter_staff"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)

    animals = AnimalModel.list_by_shelter(user["shelter_id"])
    applications = AdoptionApplicationModel.list_for_shelter(user["shelter_id"])
    report = {
        "total_animals": len(animals),
        "available": len([a for a in animals if a["status"] == "available"]),
        "processing": len([a for a in animals if a["status"] == "processing"]),
        "adopted": len([a for a in animals if a["status"] == "adopted"]),
        "applications": len(applications),
    }
    return templates.TemplateResponse(
        "shelter_dashboard.html",
        {
            "request": request,
            "user": user,
            "animals": animals,
            "applications": applications,
            "report": report,
        },
    )


@router.post("/animals/create")
def create_animal(
    request: Request,
    species: str = Form(...),
    name: str = Form(...),
    breed: str = Form(""),
    age: int = Form(0),
    sex: str = Form("unknown"),
    size: str = Form("medium"),
    color: str = Form(""),
    health: str = Form(""),
    temperament: str = Form(""),
    description: str = Form(""),
    compatible_with_children: bool = Form(False),
    compatible_with_animals: bool = Form(False),
    status_value: str = Form("available"),
    photos: list[UploadFile] = File(default=[]),
):
    user = get_current_user(request)
    if not has_role(user, {"shelter_admin", "shelter_staff"}) or not user.get("shelter_id"):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    animal_id = AnimalModel.create(
        {
            "species": _normalize_choice(species, ALLOWED_SPECIES, "cat"),
            "breed": sanitize_text(breed),
            "name": sanitize_text(name),
            "age": age,
            "sex": _normalize_choice(sex, ALLOWED_SEX, "unknown"),
            "size": _normalize_choice(size, ALLOWED_SIZE, "medium"),
            "color": sanitize_text(color),
            "health": sanitize_text(health),
            "temperament": sanitize_text(temperament),
            "description": sanitize_text(description),
            "compatible_with_children": compatible_with_children,
            "compatible_with_animals": compatible_with_animals,
            "status": _normalize_choice(status_value, ALLOWED_ANIMAL_STATUS, "available"),
            "shelter_id": user["shelter_id"],
        }
    )
    _attach_uploaded_photos(animal_id, photos)
    return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/animals/{animal_id}/update")
def update_animal(
    request: Request,
    animal_id: int,
    species: str = Form(...),
    name: str = Form(...),
    breed: str = Form(""),
    age: int | None = Form(None),
    sex: str = Form("unknown"),
    size: str = Form("medium"),
    color: str = Form(""),
    health: str = Form(""),
    temperament: str = Form(""),
    description: str = Form(""),
    status_value: str = Form("available"),
    compatible_with_children: bool = Form(False),
    compatible_with_animals: bool = Form(False),
    photos: list[UploadFile] = File(default=[]),
):
    user = get_current_user(request)
    if not has_role(user, {"shelter_admin", "shelter_staff"}) or not user.get("shelter_id"):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    animal = AnimalModel.get_by_id(animal_id)
    if not animal or animal["shelter_id"] != user["shelter_id"]:
        return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    AnimalModel.update(
        animal_id,
        {
            "species": _normalize_choice(species, ALLOWED_SPECIES, "cat"),
            "breed": sanitize_text(breed),
            "name": sanitize_text(name),
            "age": age,
            "sex": _normalize_choice(sex, ALLOWED_SEX, "unknown"),
            "size": _normalize_choice(size, ALLOWED_SIZE, "medium"),
            "color": sanitize_text(color),
            "health": sanitize_text(health),
            "temperament": sanitize_text(temperament),
            "description": sanitize_text(description),
            "status": _normalize_choice(status_value, ALLOWED_ANIMAL_STATUS, "available"),
            "compatible_with_children": compatible_with_children,
            "compatible_with_animals": compatible_with_animals,
        },
    )
    _attach_uploaded_photos(animal_id, photos)
    return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/animals/{animal_id}/delete")
def delete_animal(request: Request, animal_id: int):
    user = get_current_user(request)
    if not has_role(user, {"shelter_admin", "shelter_staff"}) or not user.get("shelter_id"):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    animal = AnimalModel.get_by_id(animal_id)
    if not animal or animal["shelter_id"] != user["shelter_id"]:
        return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    AnimalModel.delete(animal_id)
    return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/applications/{application_id}/status")
def update_application_status(request: Request, application_id: int, status_value: str = Form(...)):
    user = get_current_user(request)
    if not has_role(user, {"shelter_admin", "shelter_staff"}):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)

    application = AdoptionApplicationModel.get_by_id(application_id)
    if not application:
        return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    animal = AnimalModel.get_by_id(application["animal_id"])
    if not animal or animal["shelter_id"] != user.get("shelter_id"):
        return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    AdoptionApplicationModel.set_status(application_id, status_value)
    if status_value == "adopted":
        AnimalModel.update_status(animal["id"], "adopted")
    elif status_value in {"new", "processing"}:
        AnimalModel.update_status(animal["id"], "processing")
    elif status_value == "rejected":
        AnimalModel.update_status(animal["id"], "available")
    return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)


@router.post("/registration-request")
def create_registration_request(
    request: Request,
    shelter_name: str = Form(...),
    shelter_city: str = Form(""),
    shelter_address: str = Form(""),
    shelter_phone: str = Form(""),
    shelter_description: str = Form(""),
    applicant_position: str = Form(""),
    comment: str = Form(""),
):
    user = get_current_user(request)
    if not has_role(user, {"shelter_staff"}):
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    if ShelterRegistrationRequestModel.has_pending_for_user(user["id"]):
        return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)

    ShelterRegistrationRequestModel.create(
        {
            "user_id": user["id"],
            "shelter_name": sanitize_text(shelter_name),
            "shelter_city": sanitize_text(shelter_city),
            "shelter_address": sanitize_text(shelter_address),
            "shelter_phone": sanitize_text(shelter_phone),
            "shelter_description": sanitize_text(shelter_description),
            "applicant_position": sanitize_text(applicant_position),
            "comment": sanitize_text(comment),
        }
    )
    return RedirectResponse("/shelter/dashboard", status_code=status.HTTP_303_SEE_OTHER)
