import re
from typing import Optional
from .models import WebSubmissionPayload

VALID_GENEROS = {"Masculino", "Feminino"}
VALID_RECEBEU_JESUS = {"Sim", "Não", "evangelico", "Vai decidir depois"}

def validate_web_submission(payload: WebSubmissionPayload) -> Optional[str]:
    """Server-side mirror of the XForm rules (Missionarios_Renovame.xml).

    Geolocalizador is intentionally NOT required here: the web form sends
    "0.0 0.0 0.0 999.0" when GPS is denied/unavailable, and exports render
    those as "[NULL,NULL]" / "Localização não capturada".
    """
    if not (payload.nome or "").strip():
        return "Nome é obrigatório."
    if not (payload.missionario or "").strip():
        return "Nome do Missionário(a) é obrigatório."
    tel_digits = re.sub(r"\D", "", payload.telefone or "")
    if not re.fullmatch(r"\d{11}", tel_digits):
        return "O telefone deve conter exatamente 11 números (Ex 75988888888)."
    if payload.idade is None or not (0 <= payload.idade <= 130):
        return "Idade é obrigatória (0 a 130)."
    if payload.genero not in VALID_GENEROS:
        return "Gênero inválido."
    if payload.recebeu_jesus not in VALID_RECEBEU_JESUS:
        return "Resposta inválida para 'Recebeu Jesus?'."
    return None
