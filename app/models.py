from typing import Optional
from pydantic import BaseModel

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

class ActionSettingPayload(BaseModel):
    cidade: str
    povoado: str
    acao: Optional[str] = None

class SubmissionUpdatePayload(BaseModel):
    data_date: Optional[str] = None
    nome: Optional[str] = None
    idade: Optional[int] = None
    telefone: Optional[str] = None
    genero: Optional[str] = None
    recebeu_jesus: Optional[str] = None
    endereco: Optional[str] = None
    geopoint: Optional[str] = None
    observacoes: Optional[str] = None
    missionario: Optional[str] = None
    cidade: Optional[str] = None
    povoado: Optional[str] = None
    acao: Optional[str] = None
