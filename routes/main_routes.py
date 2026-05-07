import json

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import RedirectResponse

from models.animal import AnimalModel
from models.application import AdoptionApplicationModel
from models.favorite import FavoriteModel
from models.shelter import ShelterModel
from routes.common import get_current_user, has_role, parse_search_filters, sanitize_text, templates


router = APIRouter(tags=["main"])


@router.get("/")
def index(request: Request):
    user = get_current_user(request)
    animals = AnimalModel.filter_animals({"status": "available"}, page=1)
    if user:
        favorite_ids = FavoriteModel.list_ids_for_user(user["id"])
        for animal in animals:
            animal["is_favorite"] = animal["id"] in favorite_ids
    shelters = ShelterModel.list_approved()
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "user": user, "animals": animals[:6], "shelters": shelters},
    )


@router.get("/search")
def search_page(request: Request):
    user = get_current_user(request)
    filters = parse_search_filters(request)
    animals = AnimalModel.filter_animals(filters, page=1)
    if user:
        favorite_ids = FavoriteModel.list_ids_for_user(user["id"])
        for animal in animals:
            animal["is_favorite"] = animal["id"] in favorite_ids
    shelters = ShelterModel.list_approved()
    cities = sorted({s["city"] for s in shelters if s.get("city")})
    return templates.TemplateResponse(
        "search.html",
        {
            "request": request,
            "user": user,
            "animals": animals,
            "shelters": shelters,
            "cities_json": json.dumps(cities, ensure_ascii=False),
        },
    )


@router.get("/animals/{animal_id}")
def animal_detail(request: Request, animal_id: int):
    user = get_current_user(request)
    animal = AnimalModel.get_by_id(animal_id)
    if not animal:
        return RedirectResponse("/search", status_code=status.HTTP_303_SEE_OTHER)
    photos = AnimalModel.get_photos(animal_id)
    is_favorite = bool(user and FavoriteModel.is_favorite(user["id"], animal_id))
    return templates.TemplateResponse(
        "animal_detail.html",
        {
            "request": request,
            "user": user,
            "animal": animal,
            "photos": photos,
            "is_favorite": is_favorite,
        },
    )


@router.post("/animals/{animal_id}/apply")
def apply_for_animal(
    request: Request,
    animal_id: int,
    applicant_name: str = Form(...),
    applicant_phone: str = Form(...),
    comment: str = Form(""),
):
    user = get_current_user(request)
    if not user:
        return RedirectResponse("/auth/login", status_code=status.HTTP_303_SEE_OTHER)
    if not has_role(user, {"user"}):
        return RedirectResponse("/", status_code=status.HTTP_303_SEE_OTHER)
    animal = AnimalModel.get_by_id(animal_id)
    if not animal:
        return RedirectResponse("/search", status_code=status.HTTP_303_SEE_OTHER)

    active_application = AdoptionApplicationModel.get_active_for_animal(animal_id)
    if animal["status"] in {"processing", "adopted"} or active_application:
        return RedirectResponse(
            f"/animals/{animal_id}?error=busy",
            status_code=status.HTTP_303_SEE_OTHER,
        )

    AdoptionApplicationModel.create(
        animal_id=animal_id,
        user_id=user["id"],
        applicant_name=sanitize_text(applicant_name),
        applicant_phone=sanitize_text(applicant_phone),
        comment=sanitize_text(comment),
    )
    AnimalModel.update_status(animal_id, "processing")
    return RedirectResponse(f"/animals/{animal_id}?success=applied", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/about")
def about_page(request: Request):
    return templates.TemplateResponse(
        "about.html",
        {"request": request, "user": get_current_user(request)},
    )
