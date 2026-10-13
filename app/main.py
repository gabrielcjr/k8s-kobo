import io
import os
import csv
import json
import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.responses import HTMLResponse, StreamingResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

from .database import init_db, insert_submission, get_all_submissions, get_stats, parse_geopoint, get_setting, set_setting
from .openrosa import (
    FORM_ID, FORM_NAME, FORM_VERSION, FORM_UUID, FORM_MD5,
    AUTH_USER, AUTH_PASS, check_credentials,
    generate_form_list_xml, generate_manifest_xml, generate_submission_success_xml,
    parse_submission_xml
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(title="KoBoToolbox Renova-me Server", version="1.0.0", lifespan=lifespan)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
FORMS_DIR = os.path.join(BASE_DIR, "forms")
XML_FORM_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame.xml")
ASSET_JSON_PATH = os.path.join(FORMS_DIR, "Missionarios_Renovame_asset.json")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# --- HEALTHCHECK ---
@app.get("/healthz")
def healthz():
    return {"status": "ok", "app": "kobo-renovame", "time": datetime.now(timezone.utc).isoformat()}

@app.get("/sw.js")
@app.get("/x/offline-app-worker.js")
def get_service_worker():
    sw_path = os.path.join(STATIC_DIR, "sw.js")
    if not os.path.exists(sw_path):
        raise HTTPException(status_code=404, detail="Service worker not found")
    with open(sw_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/javascript; charset=utf-8",
        headers={
            "Content-Type": "application/javascript; charset=utf-8",
            "Service-Worker-Allowed": "/",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@app.get("/manifest.json")
def get_manifest_json():
    manifest_path = os.path.join(STATIC_DIR, "manifest.json")
    if not os.path.exists(manifest_path):
        raise HTTPException(status_code=404, detail="Manifest not found")
    with open(manifest_path, "r", encoding="utf-8") as f:
        content = f.read()
    return Response(
        content=content,
        media_type="application/manifest+json; charset=utf-8",
        headers={
            "Content-Type": "application/manifest+json; charset=utf-8",
            "Cache-Control": "no-cache"
        }
    )

# --- STATIC MEDIA ASSETS ---
@app.get("/media/{filename}")
def get_media(filename: str):
    file_path = os.path.join(STATIC_DIR, filename)
    if not os.path.exists(file_path):
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
    cidade: Optional[str] = None
    povoado: Optional[str] = None
    acao: Optional[str] = None

@app.post("/api/submit")
def api_submit(payload: WebSubmissionPayload):
    new_uuid = str(uuid.uuid4())
    inserted_id = insert_submission(
        uuid=new_uuid,
        form_id=FORM_ID,
        version=FORM_VERSION,
        data_date=payload.data_date or datetime.now(timezone.utc).strftime("%Y-%m-%d"),
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
        source="web",
        cidade=payload.cidade,
        povoado=payload.povoado,
        acao=payload.acao
    )
    return {"status": "success", "id": inserted_id, "uuid": new_uuid}

class ActionSettingPayload(BaseModel):
    cidade: str
    povoado: str
    acao: Optional[str] = None

@app.get("/api/admin/active-action")
@app.get("/api/admin/get-active-action")
def get_active_action_endpoint():
    return {
        "active_cidade": get_setting("active_cidade", "Cruz das Almas"),
        "active_povoado": get_setting("active_povoado", "Centro"),
        "active_acao": get_setting("active_acao", "Missão Cruz das Almas")
    }

@app.post("/api/admin/set-active-action")
def set_active_action(payload: ActionSettingPayload, authorization: Optional[str] = Header(None)):
    if authorization and not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBoToolbox"'}
        )
    set_setting("active_cidade", payload.cidade.strip())
    set_setting("active_povoado", payload.povoado.strip())
    if payload.acao:
        set_setting("active_acao", payload.acao.strip())
    return {
        "status": "success",
        "active_cidade": get_setting("active_cidade", "Cruz das Almas"),
        "active_povoado": get_setting("active_povoado", "Centro"),
        "active_acao": get_setting("active_acao", "Missão Cruz das Almas")
    }

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
    active_cidade = get_setting("active_cidade", "Cruz das Almas")
    active_povoado = get_setting("active_povoado", "Centro")
    active_acao = get_setting("active_acao", "Missão Cruz das Almas")

    return templates.TemplateResponse(request=request, name="dashboard.html", context={
        "submissions": submissions,
        "stats": stats,
        "base_url": base_url,
        "active_cidade": active_cidade,
        "active_povoado": active_povoado,
        "active_acao": active_acao
    })

@app.get("/api/dashboard/live")
def get_dashboard_live(authorization: Optional[str] = Header(None)):
    if not authorization or not check_credentials(authorization):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )
    submissions = get_all_submissions()
    stats = get_stats()
    return JSONResponse(
        content={
            "total": len(submissions),
            "stats": stats,
            "submissions": submissions,
            "timestamp": datetime.now(timezone.utc).isoformat()
        },
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Access-Control-Allow-Origin": "*"
        }
    )

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

    filename = f"Missionarios_Renovame_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )

def format_kobo_csv(submissions, labels: bool = False, delimiter: str = ",") -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)

    if labels:
        headers = [
            "Data", "Nome", "Idade", "Telefone", "Gênero", "Recebeu Jesus?",
            "Endereço ou referência", "Geolocalizador", "_Geolocalizador_latitude",
            "_Geolocalizador_longitude", "_Geolocalizador_altitude", "_Geolocalizador_precision",
            "Observações", "Nome do Missionário(a)", "_id", "_uuid", "_submission_time", "_origem"
        ]
        writer.writerow(headers)
        for idx, s in enumerate(submissions):
            rec_jesus = s.get("recebeu_jesus") or ""
            if rec_jesus == "evangelico":
                rec_jesus = "É evangélico(a)"
            elif rec_jesus == "Vai decidir depois":
                rec_jesus = "Ficou de decidir ainda"

            writer.writerow([
                s.get("data_date") or "",
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                s.get("telefone") or "",
                s.get("genero") or "",
                rec_jesus,
                s.get("endereco") or "",
                s.get("geopoint") or "",
                s.get("latitude") if s.get("latitude") is not None else "",
                s.get("longitude") if s.get("longitude") is not None else "",
                s.get("altitude") if s.get("altitude") is not None else "",
                s.get("precision") if s.get("precision") is not None else "",
                s.get("observacoes") or "",
                s.get("missionario") or "",
                s.get("id"),
                s.get("uuid") or "",
                s.get("submission_time") or "",
                "KoBoCollect" if s.get("source") == "kobo_collect" else "Web"
            ])
    else:
        headers = [
            "start", "end", "today", "deviceid", "Data", "Nome", "Idade",
            "Telefone", "Genero", "Recebeu_a_Jesus", "Endereco_ou_referencia",
            "Geolocalizador", "_Geolocalizador_latitude", "_Geolocalizador_longitude",
            "_Geolocalizador_altitude", "_Geolocalizador_precision", "Observacoes",
            "Nome_do_Mission_rio_a", "__version__", "_id", "_uuid", "_submission_time",
            "_validation_status", "_notes", "_status", "_submitted_by", "_tags", "_index"
        ]
        writer.writerow(headers)
        for idx, s in enumerate(submissions):
            writer.writerow([
                s.get("submission_time") or "",
                s.get("submission_time") or "",
                s.get("data_date") or (s.get("submission_time") or "")[:10],
                s.get("device_id") or "",
                s.get("data_date") or "",
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                s.get("telefone") or "",
                s.get("genero") or "",
                s.get("recebeu_jesus") or "",
                s.get("endereco") or "",
                s.get("geopoint") or "",
                s.get("latitude") if s.get("latitude") is not None else "",
                s.get("longitude") if s.get("longitude") is not None else "",
                s.get("altitude") if s.get("altitude") is not None else "",
                s.get("precision") if s.get("precision") is not None else "",
                s.get("observacoes") or "",
                s.get("missionario") or "",
                s.get("version") or FORM_VERSION,
                s.get("id"),
                s.get("uuid") or "",
                s.get("submission_time") or "",
                "",
                "[]",
                "submitted_via_web" if s.get("source") == "web" else "submitted_via_app",
                s.get("submitted_by") or "renovamechurch",
                "[]",
                str(idx + 1)
            ])

    return buf.getvalue()

def format_campo_missionarios_csv(
    submissions,
    cidade: str = "Cruz das Almas",
    povoado: str = "Centro",
    date_format: str = "month_year",
    layout: str = "clean",
    formula_sep: str = ";",
    delimiter: str = ","
) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)

    if layout == "exact_16":
        # Estrutura de 16 colunas A..P para coincidir perfeitamente com a planilha onde I, K e N estão ocultas
        headers = [
            "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Whatsapp",
            "Gênero", "", "Recebeu a Jesus?", "", "Endereço ou referência",
            "Observações", "", "Localizador", "Missionário(a)"
        ]
        writer.writerow(headers)
        for s in submissions:
            d_str = s.get("data_date") or ""
            if d_str and len(d_str) >= 7:
                parts = d_str.split("-")
                if date_format == "month_year":
                    d_val = f"{parts[1]}/{parts[0]}" if len(parts) >= 2 else d_str
                elif date_format == "full":
                    d_val = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else d_str
                else:
                    d_val = d_str
            else:
                d_val = d_str

            tel = (s.get("telefone") or "").strip()
            tel_digits = "".join(ch for ch in tel if ch.isdigit())
            if tel_digits:
                wa_formula = f'=HYPERLINK("https://api.whatsapp.com/send?phone=55{tel_digits}"{formula_sep} "Chamar no WhatsApp")'
            else:
                wa_formula = ""

            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                map_formula = f'=HYPERLINK("https://www.google.com/maps?q={lat},{lon}"{formula_sep} "Ver no mapa")'
            else:
                map_formula = ""

            # Resolução dinâmica: prioriza valor da ação gravado na submissão,
            # permitindo também sobrescrita se o usuário passar cidade/povoado específicos na URL.
            sub_cid = (s.get("cidade") or "").strip()
            sub_pov = (s.get("povoado") or "").strip()

            if cidade and cidade.strip() and cidade.strip() != "Cruz das Almas":
                row_cidade = cidade.strip()
            else:
                row_cidade = sub_cid or (cidade.strip() if cidade else "Cruz das Almas")

            if povoado and povoado.strip() and povoado.strip() != "Centro":
                row_povoado = povoado.strip()
            else:
                row_povoado = sub_pov or (povoado.strip() if povoado else "Centro")

            writer.writerow([
                d_val,
                row_cidade,
                row_povoado,
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                tel,
                wa_formula,
                s.get("genero") or "",
                "", # Coluna I (oculta)
                s.get("recebeu_jesus") or "", # Coluna J
                "", # Coluna K (oculta)
                s.get("endereco") or "", # Coluna L
                s.get("observacoes") or "", # Coluna M
                s.get("geopoint") or "", # Coluna N (oculta com coordenadas brutas)
                map_formula, # Coluna O
                s.get("missionario") or "" # Coluna P
            ])
    else:
        # Layout limpo com as 13 colunas correspondentes à visualização da tabela
        headers = [
            "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Whatsapp",
            "Gênero", "Recebeu a Jesus?", "Endereço ou referência", "Observações",
            "Localizador", "Missionário(a)"
        ]
        writer.writerow(headers)
        for s in submissions:
            d_str = s.get("data_date") or ""
            if d_str and len(d_str) >= 7:
                parts = d_str.split("-")
                if date_format == "month_year":
                    d_val = f"{parts[1]}/{parts[0]}" if len(parts) >= 2 else d_str
                elif date_format == "full":
                    d_val = f"{parts[2]}/{parts[1]}/{parts[0]}" if len(parts) == 3 else d_str
                else:
                    d_val = d_str
            else:
                d_val = d_str

            tel = (s.get("telefone") or "").strip()
            tel_digits = "".join(ch for ch in tel if ch.isdigit())
            if tel_digits:
                wa_formula = f'=HYPERLINK("https://api.whatsapp.com/send?phone=55{tel_digits}"{formula_sep} "Chamar no WhatsApp")'
            else:
                wa_formula = ""

            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                map_formula = f'=HYPERLINK("https://www.google.com/maps?q={lat},{lon}"{formula_sep} "Ver no mapa")'
            else:
                map_formula = ""

            sub_cid = (s.get("cidade") or "").strip()
            sub_pov = (s.get("povoado") or "").strip()

            if cidade and cidade.strip() and cidade.strip() != "Cruz das Almas":
                row_cidade = cidade.strip()
            else:
                row_cidade = sub_cid or (cidade.strip() if cidade else "Cruz das Almas")

            if povoado and povoado.strip() and povoado.strip() != "Centro":
                row_povoado = povoado.strip()
            else:
                row_povoado = sub_pov or (povoado.strip() if povoado else "Centro")

            writer.writerow([
                d_val,
                row_cidade,
                row_povoado,
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                tel,
                wa_formula,
                s.get("genero") or "",
                s.get("recebeu_jesus") or "",
                s.get("endereco") or "",
                s.get("observacoes") or "",
                map_formula,
                s.get("missionario") or ""
            ])

    return buf.getvalue()

def format_kobo_json(submissions):
    results = []
    for idx, s in enumerate(submissions):
        results.append({
            "_id": s.get("id"),
            "formhub/uuid": FORM_UUID,
            "start": s.get("submission_time"),
            "end": s.get("submission_time"),
            "today": s.get("data_date"),
            "deviceid": s.get("device_id") or "web-browser",
            "Data": s.get("data_date"),
            "Nome": s.get("nome"),
            "Idade": s.get("idade"),
            "Telefone": s.get("telefone"),
            "Genero": s.get("genero"),
            "Recebeu_a_Jesus": s.get("recebeu_jesus"),
            "Endereco_ou_referencia": s.get("endereco"),
            "Geolocalizador": s.get("geopoint"),
            "_Geolocalizador_latitude": s.get("latitude"),
            "_Geolocalizador_longitude": s.get("longitude"),
            "_Geolocalizador_altitude": s.get("altitude"),
            "_Geolocalizador_precision": s.get("precision"),
            "Observacoes": s.get("observacoes"),
            "Nome_do_Mission_rio_a": s.get("missionario"),
            "__version__": s.get("version") or FORM_VERSION,
            "meta/instanceID": f"uuid:{s.get('uuid')}",
            "_xform_id_string": FORM_ID,
            "_uuid": s.get("uuid"),
            "_submission_time": s.get("submission_time"),
            "_validation_status": {},
            "_notes": [],
            "_status": "submitted_via_web" if s.get("source") == "web" else "submitted_via_app",
            "_submitted_by": s.get("submitted_by") or "renovamechurch",
            "_tags": [],
            "_index": idx + 1
        })
    return {"count": len(results), "next": None, "previous": None, "results": results}

def serve_csv_response(labels: bool = False, delimiter: str = ","):
    submissions = get_all_submissions()
    csv_content = format_kobo_csv(submissions, labels=labels, delimiter=delimiter)
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'inline; filename="data.csv"',
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

# --- GOOGLE SHEETS "CAMPO MISSIONÁRIOS" SPECIALIZED CSV ENDPOINTS ---
@app.get("/campo-missionarios.csv")
@app.head("/campo-missionarios.csv")
@app.get("/sheets.csv")
@app.head("/sheets.csv")
@app.get("/api/export/campo-missionarios.csv")
@app.head("/api/export/campo-missionarios.csv")
def get_campo_missionarios_csv(
    cidade: Optional[str] = "Cruz das Almas",
    povoado: Optional[str] = "Centro",
    date_format: Optional[str] = "month_year",
    layout: Optional[str] = "clean",
    formula_sep: Optional[str] = ";",
    delimiter: Optional[str] = ","
):
    if cidade and cidade.strip() and cidade.strip() != "Cruz das Almas":
        filtered = get_all_submissions(cidade=cidade, povoado=povoado if (povoado and povoado != "Centro") else None)
        submissions = filtered if filtered else get_all_submissions()
    else:
        submissions = get_all_submissions()
    csv_content = format_campo_missionarios_csv(
        submissions,
        cidade=cidade or "Cruz das Almas",
        povoado=povoado or "Centro",
        date_format=date_format or "month_year",
        layout=layout or "clean",
        formula_sep=formula_sep or ";",
        delimiter=delimiter or ","
    )
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": 'inline; filename="campo_missionarios.csv"',
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

# --- GOOGLE SHEETS & KOBOTOOLBOX DATA CSV ENDPOINTS ---
@app.get("/data.csv")
@app.head("/data.csv")
@app.get("/api/export/csv")
@app.head("/api/export/csv")
@app.get("/api/v2/assets/{asset_id}/data.csv")
@app.head("/api/v2/assets/{asset_id}/data.csv")
@app.get("/api/v2/assets/{asset_id}/data.csv/")
@app.head("/api/v2/assets/{asset_id}/data.csv/")
@app.get("/api/v2/assets/{asset_id}/export-settings/{export_id}/data.csv")
@app.head("/api/v2/assets/{asset_id}/export-settings/{export_id}/data.csv")
@app.get("/api/v1/data/{form_id}.csv")
@app.head("/api/v1/data/{form_id}.csv")
def get_kobo_csv_endpoint(
    asset_id: Optional[str] = None,
    export_id: Optional[str] = None,
    form_id: Optional[str] = None,
    labels: Optional[bool] = False,
    lang: Optional[str] = None,
    format: Optional[str] = None,
    view: Optional[str] = None,
    cidade: Optional[str] = "Cruz das Almas",
    povoado: Optional[str] = "Centro",
    date_format: Optional[str] = "month_year",
    layout: Optional[str] = "clean",
    formula_sep: Optional[str] = ";",
    delimiter: Optional[str] = ","
):
    if format in ("sheets", "campo_missionarios") or view in ("sheets", "campo_missionarios"):
        return get_campo_missionarios_csv(
            cidade=cidade, povoado=povoado, date_format=date_format,
            layout=layout, formula_sep=formula_sep, delimiter=delimiter
        )
    use_labels = labels or (lang in ("pt", "portugues", "labels", "human"))
    return serve_csv_response(labels=use_labels, delimiter=delimiter or ",")

# --- GOOGLE SHEETS & KOBOTOOLBOX DATA JSON ENDPOINTS ---
@app.get("/data.json")
@app.head("/data.json")
@app.get("/api/v2/assets/{asset_id}/data.json")
@app.head("/api/v2/assets/{asset_id}/data.json")
@app.get("/api/v2/assets/{asset_id}/data")
@app.head("/api/v2/assets/{asset_id}/data")
@app.get("/api/v2/assets/{asset_id}/data/")
@app.head("/api/v2/assets/{asset_id}/data/")
@app.get("/api/v1/data/{form_id}.json")
@app.head("/api/v1/data/{form_id}.json")
def get_kobo_json_endpoint(asset_id: Optional[str] = None, form_id: Optional[str] = None):
    submissions = get_all_submissions()
    return JSONResponse(
        content=format_kobo_json(submissions),
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )

@app.get("/api/v1/data/{form_id}")
def get_v1_data_array(form_id: str):
    submissions = get_all_submissions()
    data = format_kobo_json(submissions)
    return JSONResponse(
        content=data["results"],
        headers={
            "Access-Control-Allow-Origin": "*",
            "Cache-Control": "no-cache"
        }
    )

# --- GEOJSON GIS EXPORT ---
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
    return JSONResponse(
        content=geojson,
        headers={"Access-Control-Allow-Origin": "*"}
    )

# --- KOBOTOOLBOX API V2 ASSET & FORM METADATA ---
@app.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ.json")
@app.get("/api/v2/assets/a7FqboN3tiXKPo6hSc8MzJ")
@app.get("/api/v2/assets/{asset_id}.json")
@app.get("/api/v2/assets/{asset_id}")
def get_asset_v2(asset_id: Optional[str] = None):
    if os.path.exists(ASSET_JSON_PATH):
        with open(ASSET_JSON_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            # update host urls to kobo.gabrielcjr.website
            return JSONResponse(content=data)
    return {"uid": FORM_ID, "name": FORM_NAME}

@app.get("/api/v2/assets/{asset_id}/export-settings/")
@app.get("/api/v2/assets/{asset_id}/export-settings")
def get_export_settings_v2(asset_id: str, request: Request):
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host", request.headers.get("host", request.url.netloc))
    base_url = f"{proto}://{host}"

    return [{
        "uid": "esjanp2i9bM7zAYduBVtzXe",
        "url": f"{base_url}/api/v2/assets/{asset_id}/export-settings/esjanp2i9bM7zAYduBVtzXe/",
        "data_url_csv": f"{base_url}/api/v2/assets/{asset_id}/export-settings/esjanp2i9bM7zAYduBVtzXe/data.csv",
        "data_url_xlsx": f"{base_url}/api/export/xlsx",
        "name": "Exportação Padrão",
        "date_modified": datetime.now(timezone.utc).isoformat()
    }]

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
