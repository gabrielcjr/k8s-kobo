import io
import csv
from typing import Optional, List, Dict, Any
from fastapi import Response

from ..openrosa import FORM_VERSION

def format_kobo_csv(submissions: List[Dict[str, Any]], labels: bool = False, delimiter: str = ",") -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)

    if labels:
        headers = [
            "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Gênero", "Recebeu Jesus?",
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
                s.get("cidade") or "",
                s.get("povoado") or "",
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
            "start", "end", "today", "deviceid", "Data", "cidade", "povoado", "Nome", "Idade",
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
                s.get("cidade") or "",
                s.get("povoado") or "",
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
    submissions: List[Dict[str, Any]],
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    date_format: str = "month_year",
    layout: str = "exact_16",
    start_row: int = 2,
    formula_sep: str = ";",
    delimiter: str = ","
) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=delimiter)

    if layout == "exact_16":
        headers = [
            "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Whatsapp",
            "Gênero", "", "Recebeu a Jesus?", "", "Endereço ou referência",
            "Observações", "GeoLocalizador", "Localizador", "Missionário(a)"
        ]
        writer.writerow(headers)
        for idx, s in enumerate(submissions):
            row_num = start_row + idx

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
            tel_val = tel_digits if tel_digits else (tel if tel else "")

            # WhatsApp formula
            wa_formula = (
                f'=IF(ISBLANK(F{row_num}){formula_sep} ""{formula_sep} '
                f'IF(F{row_num} = 0{formula_sep} "Telefone não informado"{formula_sep} '
                f'HYPERLINK("https://wa.me/55" & F{row_num}{formula_sep} "Chamar no WhatsApp")))'
            )

            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                geo_val = f"[{lat},{lon}]"
            else:
                geo_val = "[NULL,NULL]"

            # Map formula
            map_formula = (
                f'=IF(ISBLANK(N{row_num}){formula_sep} ""{formula_sep} '
                f'IF(N{row_num} = "[NULL,NULL]"{formula_sep} "Localização não capturada"{formula_sep} '
                f'IF(N{row_num} = "[0.1,0.1]"{formula_sep} "Localização não capturada"{formula_sep} '
                f'IF(N{row_num} = "[1,1]"{formula_sep} "Localização não capturada"{formula_sep} '
                f'IF(N{row_num} = "[1,2]"{formula_sep} "Localização não capturada"{formula_sep} '
                f'HYPERLINK("https://www.google.com/maps?q=" & REGEXEXTRACT(N{row_num}{formula_sep} "-?\\d+\\.\\d+,-?\\d+\\.\\d+"){formula_sep} "Ver no mapa"))))))'
            )

            sub_cid = (s.get("cidade") or "").strip()
            sub_pov = (s.get("povoado") or "").strip()

            row_cidade = (cidade.strip() if cidade and cidade.strip() else None) or sub_cid or "Cruz das Almas"
            row_povoado = (povoado.strip() if povoado and povoado.strip() else None) or sub_pov or "Centro"

            writer.writerow([
                d_val,
                row_cidade,
                row_povoado,
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                tel_val,
                wa_formula,
                s.get("genero") or "",
                "", # Coluna I (oculta)
                s.get("recebeu_jesus") or "", # Coluna J
                "", # Coluna K (oculta)
                s.get("endereco") or "", # Coluna L
                s.get("observacoes") or "", # Coluna M
                geo_val, # Coluna N (oculta com [lat,lon] ou [NULL,NULL])
                map_formula, # Coluna O (fórmula do mapa)
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
        for idx, s in enumerate(submissions):
            row_num = start_row + idx

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
            tel_val = tel_digits if tel_digits else (tel if tel else "")

            wa_formula = (
                f'=IF(ISBLANK(F{row_num}){formula_sep} ""{formula_sep} '
                f'IF(F{row_num} = 0{formula_sep} "Telefone não informado"{formula_sep} '
                f'HYPERLINK("https://wa.me/55" & F{row_num}{formula_sep} "Chamar no WhatsApp")))'
            )

            lat = s.get("latitude")
            lon = s.get("longitude")
            if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
                geo_val = f"[{lat},{lon}]"
                map_formula = f'=HYPERLINK("https://www.google.com/maps?q={lat},{lon}"{formula_sep} "Ver no mapa")'
            else:
                geo_val = "[NULL,NULL]"
                map_formula = "Localização não capturada"

            sub_cid = (s.get("cidade") or "").strip()
            sub_pov = (s.get("povoado") or "").strip()

            row_cidade = (cidade.strip() if cidade and cidade.strip() else None) or sub_cid or "Cruz das Almas"
            row_povoado = (povoado.strip() if povoado and povoado.strip() else None) or sub_pov or "Centro"

            writer.writerow([
                d_val,
                row_cidade,
                row_povoado,
                s.get("nome") or "",
                s.get("idade") if s.get("idade") is not None else "",
                tel_val,
                wa_formula,
                s.get("genero") or "",
                s.get("recebeu_jesus") or "",
                s.get("endereco") or "",
                s.get("observacoes") or "",
                map_formula,
                s.get("missionario") or ""
            ])

    return buf.getvalue()

def format_campo_missionarios_tsv(
    submissions: List[Dict[str, Any]],
    cidade: Optional[str] = None,
    povoado: Optional[str] = None,
    date_format: str = "month_year",
    start_row: int = 2,
    formula_sep: str = ";",
    include_headers: bool = False
) -> str:
    lines = []
    if include_headers:
        headers = [
            "Data", "Cidade", "Povoado", "Nome", "Idade", "Telefone", "Whatsapp",
            "Gênero", "", "Recebeu a Jesus?", "", "Endereço ou referência",
            "Observações", "GeoLocalizador", "Localizador", "Missionário(a)"
        ]
        lines.append("\t".join(headers))

    for idx, s in enumerate(submissions):
        row_num = start_row + idx

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
        tel_val = tel_digits if tel_digits else (tel if tel else "")

        wa_formula = (
            f'=IF(ISBLANK(F{row_num}){formula_sep} ""{formula_sep} '
            f'IF(F{row_num} = 0{formula_sep} "Telefone não informado"{formula_sep} '
            f'HYPERLINK("https://wa.me/55" & F{row_num}{formula_sep} "Chamar no WhatsApp")))'
        )

        lat = s.get("latitude")
        lon = s.get("longitude")
        if lat is not None and lon is not None and (lat != 0.0 or lon != 0.0):
            geo_val = f"[{lat},{lon}]"
        else:
            geo_val = "[NULL,NULL]"

        map_formula = (
            f'=IF(ISBLANK(N{row_num}){formula_sep} ""{formula_sep} '
            f'IF(N{row_num} = "[NULL,NULL]"{formula_sep} "Localização não capturada"{formula_sep} '
            f'IF(N{row_num} = "[0.1,0.1]"{formula_sep} "Localização não capturada"{formula_sep} '
            f'IF(N{row_num} = "[1,1]"{formula_sep} "Localização não capturada"{formula_sep} '
            f'IF(N{row_num} = "[1,2]"{formula_sep} "Localização não capturada"{formula_sep} '
            f'HYPERLINK("https://www.google.com/maps?q=" & REGEXEXTRACT(N{row_num}{formula_sep} "-?\\d+\\.\\d+,-?\\d+\\.\\d+"){formula_sep} "Ver no mapa"))))))'
        )

        sub_cid = (s.get("cidade") or "").strip()
        sub_pov = (s.get("povoado") or "").strip()

        row_cidade = (cidade.strip() if cidade and cidade.strip() else None) or sub_cid or "Cruz das Almas"
        row_povoado = (povoado.strip() if povoado and povoado.strip() else None) or sub_pov or "Centro"

        # Sanitize internal tabs and newlines from text fields
        endereco = (s.get("endereco") or "").replace("\t", " ").replace("\r", "").replace("\n", " ")
        observacoes = (s.get("observacoes") or "").replace("\t", " ").replace("\r", "").replace("\n", " ")
        nome = (s.get("nome") or "").replace("\t", " ").replace("\r", "").replace("\n", " ")
        missionario = (s.get("missionario") or "").replace("\t", " ").replace("\r", "").replace("\n", " ")

        cols = [
            d_val,
            row_cidade,
            row_povoado,
            nome,
            str(s.get("idade")) if s.get("idade") is not None else "",
            tel_val,
            wa_formula,
            s.get("genero") or "",
            "", # Coluna I
            s.get("recebeu_jesus") or "",
            "", # Coluna K
            endereco,
            observacoes,
            geo_val,
            map_formula,
            missionario
        ]
        lines.append("\t".join(cols))

    return "\n".join(lines)

def serve_csv_response(
    labels: bool = False,
    delimiter: str = ",",
    submissions: Optional[List[Dict[str, Any]]] = None,
    filename: Optional[str] = None
) -> Response:
    from ..database import get_all_submissions
    if submissions is None:
        submissions = get_all_submissions()
    csv_content = format_kobo_csv(submissions, labels=labels, delimiter=delimiter)
    fn = filename or "data.csv"
    return Response(
        content=csv_content,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Type": "text/csv; charset=utf-8",
            "Content-Disposition": f'inline; filename="{fn}"',
            "Cache-Control": "no-cache, no-store, must-revalidate"
        }
    )
