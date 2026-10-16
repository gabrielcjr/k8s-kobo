import os
import json
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse

from ..config import ASSET_JSON_PATH
from ..utils import get_effective_base_url
from ..auth import check_auth_or_401
from ..openrosa import FORM_ID, FORM_NAME
from ..database import get_all_submissions
from ..formatters import format_kobo_json

router = APIRouter(tags=["KoBoToolbox API Compatibility"])

@router.get("/data.json")
@router.head("/data.json")
@router.get("/api/v2/assets/{asset_id}/data.json")
@router.head("/api/v2/assets/{asset_id}/data.json")
@router.get("/api/v2/assets/{asset_id}/data")
@router.head("/api/v2/assets/{asset_id}/data")
@router.get("/api/v2/assets/{asset_id}/data/")
@router.head("/api/v2/assets/{asset_id}/data/")
@router.get("/api/v1/data/{form_id}.json")
@router.head("/api/v1/data/{form_id}.json")
def get_kobo_json_endpoint(
    request: Request,
    asset_id: Optional[str] = None,
    form_id: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err
    submissions = get_all_submissions()
    return JSONResponse(
        content=format_kobo_json(submissions),
        headers={
            "Cache-Control": "no-cache"
        }
    )

@router.get("/api/v1/data/{form_id}")
@router.head("/api/v1/data/{form_id}")
def get_v1_data_array(
    request: Request,
    form_id: str,
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err
    submissions = get_all_submissions()
    data = format_kobo_json(submissions)
    return JSONResponse(
        content=data["results"],
        headers={
            "Cache-Control": "no-cache"
        }
    )

@router.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ.json")
@router.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ")
@router.get("/api/v2/assets/{asset_id}.json")
@router.get("/api/v2/assets/{asset_id}")
def get_asset_v2(asset_id: Optional[str] = None):
    if os.path.exists(ASSET_JSON_PATH):
        with open(ASSET_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return JSONResponse(content=data)
    return {"uid": FORM_ID, "name": FORM_NAME}

@router.get("/api/v2/assets/{asset_id}/export-settings/")
@router.get("/api/v2/assets/{asset_id}/export-settings")
def get_export_settings_v2(asset_id: str, request: Request):
    base_url = get_effective_base_url(request)
    return [{
        "uid": "esjanp2i9bM7zAYduBVtzXe",
        "url": f"{base_url}/api/v2/assets/{asset_id}/export-settings/esjanp2i9bM7zAYduBVtzXe/",
        "data_url_csv": f"{base_url}/api/v2/assets/{asset_id}/export-settings/esjanp2i9bM7zAYduBVtzXe/data.csv",
        "data_url_xlsx": f"{base_url}/api/export/xlsx",
        "name": "Exportação Padrão",
        "date_modified": datetime.now(timezone.utc).isoformat()
    }]

@router.get("/api/v1/forms")
def get_v1_forms(request: Request):
    base_url = get_effective_base_url(request)
    return [{
        "formid": 1,
        "id_string": FORM_ID,
        "title": FORM_NAME,
        "description": FORM_NAME,
        "url": f"{base_url}/formXml?formId={FORM_ID}"
    }]
