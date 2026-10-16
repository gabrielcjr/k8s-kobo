from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Response, Header, Request
from fastapi.responses import StreamingResponse, JSONResponse

from ..utils import sanitize_filename_part
from ..auth import check_auth_or_401
from ..database import get_all_submissions
from ..formatters import (
    generate_missionarios_xlsx,
    format_campo_missionarios_csv,
    format_campo_missionarios_tsv,
    serve_csv_response,
    build_geojson
)

router = APIRouter(tags=["Exports"])

@router.get("/api/export/xlsx")
@router.head("/api/export/xlsx")
def export_xlsx(
    request: Request,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err

    submissions = get_all_submissions(
        cidade=cidade,
        povoado=povoado,
        recebeu_jesus=recebeu_jesus,
        missionario=missionario,
        genero=genero,
        search=search,
        data_date=data_date
    )

    buf, filename = generate_missionarios_xlsx(submissions, cidade=cidade, povoado=povoado)

    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/campo-missionarios.csv")
@router.head("/campo-missionarios.csv")
@router.get("/sheets.csv")
@router.head("/sheets.csv")
@router.get("/api/export/campo-missionarios.csv")
@router.head("/api/export/campo-missionarios.csv")
def get_campo_missionarios_csv(
    request: Request,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None,
    date_format: Optional[str] = "month_year",
    layout: Optional[str] = "exact_16",
    start_row: Optional[int] = 2,
    formula_sep: Optional[str] = ";",
    delimiter: Optional[str] = ",",
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err

    if cidade and cidade.strip():
        filtered = get_all_submissions(
            cidade=cidade.strip(),
            povoado=povoado.strip() if povoado else None,
            recebeu_jesus=recebeu_jesus,
            missionario=missionario,
            genero=genero,
            search=search,
            data_date=data_date
        )
        submissions = filtered if filtered else get_all_submissions()
    else:
        submissions = get_all_submissions(
            recebeu_jesus=recebeu_jesus,
            missionario=missionario,
            genero=genero,
            search=search,
            data_date=data_date
        )

    csv_content = format_campo_missionarios_csv(
        submissions,
        cidade=cidade,
        povoado=povoado,
        date_format=date_format or "month_year",
        layout=layout or "exact_16",
        start_row=start_row or 2,
        formula_sep=formula_sep or ";",
        delimiter=delimiter or ","
    )
    filename = "campo_missionarios.csv"
    if cidade and cidade.strip():
        safe_cidade = sanitize_filename_part(cidade.strip())
        filename = f"campo_missionarios_{safe_cidade}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/api/dashboard/copy-tsv")
@router.head("/api/dashboard/copy-tsv")
def get_dashboard_copy_tsv(
    request: Request,
    start_row: int = 2,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None,
    date_format: str = "month_year",
    formula_sep: str = ";",
    headers: bool = False,
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err

    if cidade and cidade.strip():
        submissions = get_all_submissions(
            cidade=cidade.strip(),
            povoado=povoado.strip() if povoado else None,
            recebeu_jesus=recebeu_jesus,
            missionario=missionario,
            genero=genero,
            search=search,
            data_date=data_date
        )
    else:
        submissions = get_all_submissions(
            recebeu_jesus=recebeu_jesus,
            missionario=missionario,
            genero=genero,
            search=search,
            data_date=data_date
        )

    tsv_content = format_campo_missionarios_tsv(
        submissions,
        cidade=cidade,
        povoado=povoado,
        date_format=date_format,
        start_row=start_row,
        formula_sep=formula_sep,
        include_headers=headers
    )
    filename = "campo_missionarios.tsv"
    if cidade and cidade.strip():
        safe_cidade = sanitize_filename_part(cidade.strip())
        filename = f"campo_missionarios_{safe_cidade}.tsv"

    return Response(
        content=tsv_content,
        media_type="text/tab-separated-values; charset=utf-8",
        headers={
            "Content-Type": "text/tab-separated-values; charset=utf-8",
            "Content-Disposition": f'inline; filename="{filename}"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )

@router.get("/data.csv")
@router.head("/data.csv")
@router.get("/api/export/csv")
@router.head("/api/export/csv")
@router.get("/api/v2/assets/{asset_id}/data.csv")
@router.head("/api/v2/assets/{asset_id}/data.csv")
@router.get("/api/v2/assets/{asset_id}/data.csv/")
@router.head("/api/v2/assets/{asset_id}/data.csv/")
@router.get("/api/v2/assets/{asset_id}/export-settings/{export_id}/data.csv")
@router.head("/api/v2/assets/{asset_id}/export-settings/{export_id}/data.csv")
@router.get("/api/v1/data/{form_id}.csv")
@router.head("/api/v1/data/{form_id}.csv")
def get_kobo_csv_endpoint(
    request: Request,
    asset_id: Optional[str] = None,
    export_id: Optional[str] = None,
    form_id: Optional[str] = None,
    labels: Optional[bool] = False,
    lang: Optional[str] = None,
    format: Optional[str] = None,
    view: Optional[str] = None,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None,
    date_format: Optional[str] = "month_year",
    layout: Optional[str] = "exact_16",
    start_row: Optional[int] = 2,
    formula_sep: Optional[str] = ";",
    delimiter: Optional[str] = ",",
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err

    if format in ("sheets", "campo_missionarios") or view in ("sheets", "campo_missionarios"):
        return get_campo_missionarios_csv(
            request=request,
            cidade=cidade, povoado=povoado,
            recebeu_jesus=recebeu_jesus, missionario=missionario,
            genero=genero, search=search, data_date=data_date,
            date_format=date_format,
            layout=layout, start_row=start_row, formula_sep=formula_sep,
            delimiter=delimiter, authorization=authorization
        )

    use_labels = labels or (lang in ("pt", "portugues", "labels", "human"))
    submissions = get_all_submissions(
        cidade=cidade,
        povoado=povoado,
        recebeu_jesus=recebeu_jesus,
        missionario=missionario,
        genero=genero,
        search=search,
        data_date=data_date
    )
    fn = "data.csv"
    if cidade and cidade.strip():
        safe_cidade = sanitize_filename_part(cidade.strip())
        fn = f"data_{safe_cidade}.csv"

    return serve_csv_response(labels=use_labels, delimiter=delimiter or ",", submissions=submissions, filename=fn)

@router.get("/api/export/geojson")
@router.head("/api/export/geojson")
def export_geojson(
    request: Request,
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    recebeu_jesus: Optional[str] = None,
    missionario: Optional[str] = None,
    genero: Optional[str] = None,
    search: Optional[str] = None,
    data_date: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    auth_err = check_auth_or_401(authorization=authorization, request=request)
    if auth_err:
        return auth_err

    submissions = get_all_submissions(
        cidade=cidade,
        povoado=povoado,
        recebeu_jesus=recebeu_jesus,
        missionario=missionario,
        genero=genero,
        search=search,
        data_date=data_date
    )

    geojson = build_geojson(submissions)
    return JSONResponse(
        content=geojson,
        headers={"Cache-Control": "no-cache"}
    )
