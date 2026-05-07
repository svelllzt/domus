from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from models.animal import AnimalModel
from models.favorite import FavoriteModel
from routes.common import get_current_user, has_role, parse_search_filters


router = APIRouter(prefix="/api", tags=["api"])


@router.get("/animals/filter")
def filter_animals(request: Request):
    filters = parse_search_filters(request)
    page = int(request.query_params.get("page", 1) or 1)
    animals = AnimalModel.filter_animals(filters, page=page)
    user = get_current_user(request)
    if user:
        favorite_ids = FavoriteModel.list_ids_for_user(user["id"])
        for animal in animals:
            animal["is_favorite"] = animal["id"] in favorite_ids
    total = AnimalModel.count_filtered(filters)
    return JSONResponse({"animals": animals, "total": total, "page": page})


@router.post("/favorites/{animal_id}/toggle")
def toggle_favorite(request: Request, animal_id: int):
    user = get_current_user(request)
    if not user:
        return JSONResponse({"error": "auth_required"}, status_code=401)
    if not has_role(user, {"user"}):
        return JSONResponse({"error": "auth_required"}, status_code=401)
    if FavoriteModel.is_favorite(user["id"], animal_id):
        FavoriteModel.remove(user["id"], animal_id)
        return JSONResponse({"is_favorite": False})
    FavoriteModel.add(user["id"], animal_id)
    return JSONResponse({"is_favorite": True})
