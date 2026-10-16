import re
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse

from ..config import templates
from ..models import WebSubmissionPayload
from ..validation import validate_web_submission
from ..database import insert_submission
from ..openrosa import FORM_ID, FORM_VERSION

router = APIRouter(tags=["Web Form"])

@router.get("/", response_class=HTMLResponse)
def index_page(request: Request):
    return templates.TemplateResponse(request=request, name="webform.html", context={})

@router.get("/x/{enketo_id}", response_class=HTMLResponse)
def enketo_form_page(enketo_id: str, request: Request):
    return templates.TemplateResponse(request=request, name="webform.html", context={"enketo_id": enketo_id})

@router.post("/api/submit")
def api_submit(payload: WebSubmissionPayload):
    error = validate_web_submission(payload)
    if error:
        raise HTTPException(status_code=422, detail=error)
    payload.telefone = re.sub(r"\D", "", payload.telefone)
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
