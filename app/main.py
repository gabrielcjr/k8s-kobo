from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .config import STATIC_DIR
from .database import init_db
from .routers import (
    core_router,
    openrosa_router,
    webform_router,
    dashboard_router,
    exports_router,
    kobo_api_router
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="KoBoToolbox Renova-me Server",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static assets
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include domain-specific routers
app.include_router(core_router)
app.include_router(openrosa_router)
app.include_router(webform_router)
app.include_router(dashboard_router)
app.include_router(exports_router)
app.include_router(kobo_api_router)
