from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Request, Response, HTTPException, Header
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from ..config import templates
from ..utils import get_effective_base_url
from ..auth import check_auth_or_401, is_authenticated, set_session_cookie, COOKIE_NAME
from ..models import ActionSettingPayload, SubmissionUpdatePayload
from ..database import (
    get_all_submissions,
    get_stats,
    get_setting,
    set_setting,
    get_submission_by_id,
    update_submission,
    delete_submission
)

router = APIRouter(tags=["Admin & Dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
@router.get("/admin", response_class=HTMLResponse)
def dashboard_page(request: Request, authorization: Optional[str] = Header(None)):
    if not is_authenticated(authorization=authorization, request=request):
        return Response(
            content="Autenticação necessária para o painel.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )

    base_url = get_effective_base_url(request)
    submissions = get_all_submissions()
    stats = get_stats()
    active_cidade = get_setting("active_cidade", "Cruz das Almas")
    active_povoado = get_setting("active_povoado", "Centro")
    active_acao = get_setting("active_acao", "Missão Cruz das Almas")

    response = templates.TemplateResponse(request=request, name="dashboard.html", context={
        "submissions": submissions,
        "stats": stats,
        "base_url": base_url,
        "active_cidade": active_cidade,
        "active_povoado": active_povoado,
        "active_acao": active_acao
    })
    set_session_cookie(response)
    return response

@router.get("/logout")
def logout():
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return response

@router.get("/api/dashboard/live")
def get_dashboard_live(request: Request, authorization: Optional[str] = Header(None)):
    if not is_authenticated(authorization=authorization, request=request):
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
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/api/admin/active-action")
@router.get("/api/admin/get-active-action")
def get_active_action_endpoint():
    return {
        "active_cidade": get_setting("active_cidade", "Cruz das Almas"),
        "active_povoado": get_setting("active_povoado", "Centro"),
        "active_acao": get_setting("active_acao", "Missão Cruz das Almas")
    }

@router.post("/api/admin/set-active-action")
def set_active_action(request: Request, payload: ActionSettingPayload, authorization: Optional[str] = Header(None)):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err
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

@router.get("/api/dashboard/submissions/{submission_id}")
def api_get_submission(submission_id: int, request: Request, authorization: Optional[str] = Header(None)):
    if not is_authenticated(authorization=authorization, request=request):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )
    sub = get_submission_by_id(submission_id)
    if not sub:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return sub

@router.put("/api/dashboard/submissions/{submission_id}")
@router.post("/api/dashboard/submissions/{submission_id}/update")
def api_update_submission(
    submission_id: int,
    payload: SubmissionUpdatePayload,
    request: Request,
    authorization: Optional[str] = Header(None)
):
    if not is_authenticated(authorization=authorization, request=request):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )
    updates = {k: v for k, v in payload.model_dump().items() if v is not None}
    updated = update_submission(submission_id, updates)
    if not updated:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return {"status": "success", "submission": updated}

@router.delete("/api/dashboard/submissions/{submission_id}")
@router.post("/api/dashboard/submissions/{submission_id}/delete")
def api_delete_submission(submission_id: int, request: Request, authorization: Optional[str] = Header(None)):
    if not is_authenticated(authorization=authorization, request=request):
        return Response(
            content="Unauthorized",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Painel KoBoToolbox Renova-me"'}
        )
    deleted = delete_submission(submission_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    return {"status": "success", "id": submission_id}
