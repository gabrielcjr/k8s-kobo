from typing import Optional
from fastapi import Response
from .openrosa import check_credentials

def check_auth_or_401(authorization: Optional[str]) -> Optional[Response]:
    if not authorization or not check_credentials(authorization):
        return Response(
            content="Autenticação necessária. O acesso direto e aberto à API foi desativado por segurança dos dados.",
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="KoBo Renova-me Dados Protegidos"'}
        )
    return None
