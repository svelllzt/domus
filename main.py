import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import APP_ENV, STATIC_DIR
from database import run_migrations
from routes.admin import router as admin_router
from routes.api import router as api_router
from routes.auth import router as auth_router
from routes.main_routes import router as main_router
from routes.shelter import router as shelter_router
from routes.user import router as user_router


app = FastAPI(title="Pets Shelter Finder")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

app.include_router(main_router)
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(shelter_router)
app.include_router(admin_router)
app.include_router(api_router)


@app.on_event("startup")
def on_startup() -> None:
    run_migrations()


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=APP_ENV != "production")
