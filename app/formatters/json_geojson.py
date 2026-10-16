from typing import List, Dict, Any
from ..openrosa import FORM_ID, FORM_NAME, FORM_VERSION, FORM_UUID

def format_kobo_json(submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
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

def build_geojson(submissions: List[Dict[str, Any]]) -> Dict[str, Any]:
    features = []
    for s in submissions:
        if s.get("latitude") and s.get("longitude") and s["latitude"] != 0.0:
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [s["longitude"], s["latitude"]]
                },
                "properties": {
                    "id": s["id"],
                    "nome": s["nome"],
                    "cidade": s.get("cidade"),
                    "povoado": s.get("povoado"),
                    "telefone": s["telefone"],
                    "genero": s["genero"],
                    "recebeu_jesus": s["recebeu_jesus"],
                    "missionario": s["missionario"],
                    "data": s["data_date"],
                    "endereco": s["endereco"]
                }
            })

    return {
        "type": "FeatureCollection",
        "features": features
    }
