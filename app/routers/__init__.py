from .core import router as core_router
from .openrosa import router as openrosa_router
from .webform import router as webform_router
from .dashboard import router as dashboard_router
from .exports import router as exports_router
from .kobo_api import router as kobo_api_router

__all__ = [
    "core_router",
    "openrosa_router",
    "webform_router",
    "dashboard_router",
    "exports_router",
    "kobo_api_router"
]
