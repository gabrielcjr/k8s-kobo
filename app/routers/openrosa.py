import os
from typing import Optional
from fastapi import APIRouter, Request, Response, HTTPException, Header

from ..config import XML_FORM_PATH
from ..utils import get_effective_base_url
from ..openrosa import (
    check_credentials,
    generate_form_list_xml,
    generate_manifest_xml,
    generate_submission_success_xml,
    parse_submission_xml
)
from ..database import insert_submission

router = APIRouter(tags=["OpenRosa Protocol"])

def handle_form_list(request: Request, authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )

    effective_base_url = get_effective_base_url(request)
    xml_content = generate_form_list_xml(effective_base_url)
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@router.get("/formList")
def get_form_list_root(request: Request, authorization: Optional[str] = Header(None)):
    return handle_form_list(request, authorization)

@router.get("/{username}/formList")
def get_form_list_user(username: str, request: Request, authorization: Optional[str] = Header(None)):
    return handle_form_list(request, authorization)

def handle_form_xml(formId: Optional[str] = None):
    if not os.path.exists(XML_FORM_PATH):
        raise HTTPException(status_code=404, detail="Form XML not found")
    with open(XML_FORM_PATH, "r", encoding="utf-8") as f:
        xml_content = f.read()
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@router.get("/formXml")
def get_form_xml(formId: Optional[str] = None):
    return handle_form_xml(formId)

@router.get("/forms/{form_id}/form.xml")
def get_form_xml_path(form_id: str):
    return handle_form_xml(form_id)

@router.get("/{username}/forms/{form_id}/form.xml")
def get_form_xml_user(username: str, form_id: str):
    return handle_form_xml(form_id)

def handle_manifest(request: Request, formId: Optional[str] = None):
    effective_base_url = get_effective_base_url(request)
    xml_content = generate_manifest_xml(effective_base_url)
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@router.get("/xformsManifest")
def get_manifest(request: Request, formId: Optional[str] = None):
    return handle_manifest(request, formId)

@router.get("/forms/{form_id}/manifest.xml")
def get_manifest_path(form_id: str, request: Request):
    return handle_manifest(request, form_id)

@router.get("/{username}/forms/{form_id}/manifest.xml")
def get_manifest_user(username: str, form_id: str, request: Request):
    return handle_manifest(request, form_id)

def handle_submission_head(authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )
    return Response(
        status_code=204,
        headers={
            "X-OpenRosa-Version": "1.0",
            "X-OpenRosa-Accept-Content-Length": "10485760"
        }
    )

@router.head("/submission")
def submission_head_root(authorization: Optional[str] = Header(None)):
    return handle_submission_head(authorization)

@router.head("/{username}/submission")
def submission_head_user(username: str, authorization: Optional[str] = Header(None)):
    return handle_submission_head(authorization)

async def handle_submission_post(request: Request, authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )

    form_data = await request.form()
    xml_file = form_data.get("xml_submission_file")
    
    raw_xml_text = ""
    if hasattr(xml_file, "read"):
        contents = await xml_file.read()
        raw_xml_text = contents.decode("utf-8", errors="replace")
    elif isinstance(xml_file, str):
        raw_xml_text = xml_file
    else:
        for k, v in form_data.items():
            if hasattr(v, "read"):
                contents = await v.read()
                raw_xml_text = contents.decode("utf-8", errors="replace")
                break

    if not raw_xml_text:
        return Response(
            content="Missing submission XML file",
            status_code=400,
            headers={"X-OpenRosa-Version": "1.0"}
        )

    parsed = parse_submission_xml(raw_xml_text)
    
    insert_submission(
        uuid=parsed["uuid"],
        form_id=parsed["form_id"],
        version=parsed["version"],
        data_date=parsed["data_date"],
        nome=parsed["nome"],
        idade=parsed["idade"],
        telefone=parsed["telefone"],
        genero=parsed["genero"],
        recebeu_jesus=parsed["recebeu_jesus"],
        endereco=parsed["endereco"],
        geopoint=parsed["geopoint"],
        observacoes=parsed["observacoes"],
        missionario=parsed["missionario"],
        device_id=parsed["device_id"],
        submitted_by="renovamechurch",
        source="kobo_collect",
        raw_xml=raw_xml_text
    )

    success_xml = generate_submission_success_xml()
    return Response(
        content=success_xml,
        status_code=201,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@router.post("/submission")
async def submission_post_root(request: Request, authorization: Optional[str] = Header(None)):
    return await handle_submission_post(request, authorization)

@router.post("/{username}/submission")
async def submission_post_user(username: str, request: Request, authorization: Optional[str] = Header(None)):
    return await handle_submission_post(request, authorization)
