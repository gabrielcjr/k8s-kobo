import io
import os
import csv
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, Response, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .database import init_db, insert_submission, get_all_submissions, get_stats, parse_geopoint
from .openrosa import (
    FORM_ID, FORM_NAME, FORM_VERSION, FORM_UUID, FORM_MD5,
    AUTH_USER, AUTH_PASS, check_credentials,
    generate_form_list_xml, generate_manifest_xml, generate_submission_success_xml,
    parse_submission_xml
)

app = FastAPI(title="KoBoToolbox Renova-me Server", version="1.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
FORMS_DIR = os.path.join(BASE_DIR, "forms")
XML_FORM_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame.xml")
ASSET_JSON_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame_asset.json")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.on_event("startup")
def on_startup():
    init_db()

# --- HEALTHCHECK ---
@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "kobo-renovame", "time": datetime.utcnow().isoformat()}

# --- STATIC MEDIA ASSETS ---
@app.get("/media/{filename}")
def get_media(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
        # check unescaped
        import urllib.parse
        unescaped = urllib.parse.unquote(filename)
        file_path = os.path.join(STATIC_DIR, unescaped)
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Media file not found")
    media_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
    return StreamingResponse(open(file_path, "rb"), media_type=media_type)

@app.get("/media/get/0/PY2hbkKi/{hash_val}/{filename}")
def get_media_enketo_style(hash_val: str, filename: str):
    return get_media(filename)

# --- OPENROSA DISCOVERY: FORMLIST ---
def handle_form_list(request: Request, authorization: Optional[str] = Header(None)):
    # Support basic auth challenge if present
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )

    base_url = str(request.base_url).rstrip("/")
    # Check X-Forwarded-Proto
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    effective_base_url = f"{proto}://{host}"

    xml_content = generate_form_list_xml(effective_base_url)
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@app.get("/formList")
def get_form_list_root(request: Request, authorization: Optional[str] = Header(None)):
    return handle_form_list(request, authorization)

@app.get("/{username}/formList")
def get_form_list_user(username: str, request: Request, authorization: Optional[str] = Header(None)):
    return handle_form_list(request, authorization)

# --- OPENROSA FORM XML ---
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

@app.get("/formXml")
def get_form_xml(formId: Optional[str] = None):
    return handle_form_xml(formId)

@app.get("/forms/{form_id}/form.xml")
def get_form_xml_path(form_id: str):
    return handle_form_xml(form_id)

@app.get("/{username}/forms/{form_id}/form.xml")
def get_form_xml_user(username: str, form_id: str):
    return handle_form_xml(form_id)

# --- OPENROSA MANIFEST ---
def handle_manifest(request: Request, formId: Optional[str] = None):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    effective_base_url = f"{proto}://{host}"

    xml_content = generate_manifest_xml(effective_base_url)
    return Response(
        content=xml_content,
        media_type="text/xml; charset=utf-8",
        headers={
            "X-OpenRosa-Version": "1.0",
            "Content-Type": "text/xml; charset=utf-8"
        }
    )

@app.get("/xformsManifest")
def get_manifest(request: Request, formId: Optional[str] = None):
    return handle_manifest(request, formId)

@app.get("/forms/{form_id}/manifest.xml")
def get_manifest_path(form_id: str, request: Request):
    return handle_manifest(request, form_id)

@app.get("/{username}/forms/{form_id}/manifest.xml")
def get_manifest_user(username: str, form_id: str, request: Request):
    return handle_manifest(request, form_id)

# --- OPENROSA SUBMISSIONS (ODK / KOBOCOLLECT) ---
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

@app.head("/submission")
def submission_head_root(authorization: Optional[str] = Header(None)):
    return handle_submission_head(authorization)

@app.head("/{username}/submission")
def submission_head_user(username: str, authorization: Optional[str] = Header(None)):
    return handle_submission_head(authorization)

async def handle_submission_post(
    request: Request,
    authorization: Optional[str] = Header(None)
):
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
        # Check if form data has any file
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
    
    # Save to database
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

@app.post("/submission")
async def submission_post_root(request: Request, authorization: Optional[str] = Header(None)):
    return await handle_submission_post(request, authorization)

@app.post("/{username}/submission")
async def submission_post_user(username: str, request: Request, authorization: Optional[str] = Header(None)):
    return await handle_submission_post(request, authorization)

# --- WEB FORM INTERFACE (ENKETO-STYLE) ---
@app.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="webform.html", context={})

@app.get("/x/{enketo_id}", response_class=HTMLResponse)
def enketo_form_page(enketo_id: str, request: Request):
    return templates.TemplateResponse(request=request, name="webform.html", context={"enketo_id": enketo_id})

# --- JSON API FOR WEB FORM SUBMISSIONS ---
class WebSubmissionPayload(BaseModel):
    data_date: Optional[str] = None
    nome: str
    idade: Optional[int] = None
    telefone: str
    genero: str
    recebeu_jesus: str
    endereco: Optional[str] = None
    geopoint: Optional[str] = None
    observacoes: Optional[str] = None
    missionario: str

@app.post("/api/submit")
def api_submit(payload: WebSubmissionPayload):
    new_uuid = str(uuid.uuid4())
    inserted_id = insert_submission(
        uuid=new_uuid,
        form_id=FORM_ID,
        version=FORM_VERSION,
        data_date=payload.data_date or datetime.utcnow().strftime("%Y-%m-%d"),
        nome=payload.nome,
        idade=payload.idade,
        telefone=payload.telefone,
        genero=payload.genero,
        recebeu_jesus=payload.recebeu_jesus,
        endereco=payload.endereco,
        geopoint=payload.geopoint,
        observacoes=payload.observacoes,
        missionario=payload.missionario,
        device_id="web-browser",
        submitted_by="renovamechurch",
        source="web"
    )
    return {"status": "success", "id": inserted_id, "uuid": new_uuid}

# --- ADMIN DASHBOARD ---
@app.get("/dashboard", response_class=HTMLResponse)
@app.get("/admin", response_class=HTMLResponse)
def dashboard_page(request: Request, authorization: Optional[str] = Header(None)):
    # Basic Auth check for Dashboard
    if not authorization or not check_credentials(authorization):
        return Response(
            content="Autenticação necessária para o painel.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )

    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base_url = f"{proto}://{host}"

    submissions = get_all_submissions()
    stats = get_stats()

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "submissions": submissions,
        "stats": stats,
        "base_url": base_url
    })

# --- EXPORTS: EXCEL (.xlsx), CSV, GEOJSON ---
@app.get("/api/export/xlsx")
def export_xlsx(authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )

    submissions = get_all_submissions()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Missionários Renova-me"

    headers = [
        "_id", "Data", "Nome", "Idade", "Telefone", "Genero",
        "Recebeu_a_Jesus", "Endereco_ou_referencia", "Geolocalizador",
        "_Geolocalizador_latitude", "_Geolocalizador_longitude",
        "_Geolocalizador_altitude", "_Geolocalizador_precision",
        "Observacoes", "Nome_do_Mission_rio_a", "__version__",
        "_submission_time", "_submitted_by", "_source", "_uuid"
    ]

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="C91818", end_color="C91818", fill_type="solid")
    center_align = Alignment(horizontal="center", vertical="center")

    ws.append(headers)
    for col_num in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align

    for s in submissions:
        ws.append([
            s["id"],
            s["data_date"] or "",
            s["nome"] or "",
            s["idade"] if s["idade"] is not None else "",
            s["telefone"] or "",
            s["genero"] or "",
            s["recebeu_jesus"] or "",
            s["endereco"] or "",
            s["geopoint"] or "",
            s["latitude"] if s["latitude"] is not None else "",
            s["longitude"] if s["longitude"] is not None else "",
            s["altitude"] if s["altitude"] is not None else "",
            s["precision"] if s["precision"] is not None else "",
            s["observacoes"] or "",
            s["missionario"] or "",
            s["version"] or FORM_VERSION,
            s["submission_time"] or "",
            s["submitted_by"] or "renovamechurch",
            s["source"] or "kobo_collect",
            s["uuid"] or ""
        ])

    # Auto-adjust column width
    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = col[0].column_letter
        ws.column_dimensions[col_letter].width = max(max_len + 3, 12)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"Missionarios_Renovame_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/export/csv")
def export_csv(authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )

    submissions = get_all_submissions()
    buf = io.StringIO()
    writer = csv.writer(buf)

    headers = [
        "_id", "Data", "Nome", "Idade", "Telefone", "Genero",
        "Recebeu_a_Jesus", "Endereco_ou_referencia", "Geolocalizador",
        "_Geolocalizador_latitude", "_Geolocalizador_longitude",
        "Observacoes", "Nome_do_Mission_rio_a", "_submission_time", "_uuid"
    ]
    writer.writerow(headers)

    for s in submissions:
        writer.writerow([
            s["id"], s["data_date"], s["nome"], s["idade"], s["telefone"],
            s["genero"], s["recebeu_jesus"], s["endereco"], s["geopoint"],
            s["latitude"], s["longitude"], s["observacoes"], s["missionario"],
            s["submission_time"], s["uuid"]
        ])

    buf.seek(0)
    filename = f"Missionarios_Renovame_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

@app.get("/api/export/geojson")
def export_geojson():
    submissions = get_all_submissions()
    features = []
    for s in submissions:
        if s["latitude"] and s["longitude"] and s["latitude"] != 0.0:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [s["longitude"], s["latitude"]]
                },
                "properties": {
                    "id": s["id"],
                    "nome": s["nome"],
                    "telefone": s["telefone"],
                    "genero": s["genero"],
                    "recebeu_jesus": s["recebeu_jesus"],
                    "missionario": s["missionario"],
                    "data": s["data_date"],
                    "endereco": s["endereco"]
                }
            })

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    return JSONResponse(content=geojson)

# --- KOBOTOOLBOX API V2 COMPATIBILITY ---
@app.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ.json")
def get_asset_v2():
    if os.path.exists(ASSET_JSON_PATH):
        with open(ASSET_JSON_PATH, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    return {"uid": FORM_ID, "name": FORM_NAME}

@app.get("/api/v2/assets/{asset_id}/data.json")
def get_asset_data_v2(asset_id: str):
    submissions = get_all_submissions()
    results = []
    for s in submissions:
        results.append({
            "_id": s["id"],
            "Data": s["data_date"],
            "Nome": s["nome"],
            "Idade": s["idade"],
            "Telefone": s["telefone"],
            "Genero": s["genero"],
            "Recebeu_a_Jesus": s["recebeu_jesus"],
            "Endereco_ou_referencia": s["endereco"],
            "Geolocalizador": s["geopoint"],
            "Observacoes": s["observacoes"],
            "Nome_do_Mission_rio_a": s["missionario"],
            "_submission_time": s["submission_time"],
            "_uuid": s["uuid"]
        })
    return {"count": len(results), "results": results}

@app.get("/api/v1/forms")
def get_v1_forms(request: Request):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base_url = f"{proto}://{host}"

    return [{
        "formid": 1,
        "id_string": FORM_ID,
        "title": FORM_NAME,
        "description": FORM_NAME,
        "url": f"{base_url}/formXml?formId={FORM_ID}"
    }]
