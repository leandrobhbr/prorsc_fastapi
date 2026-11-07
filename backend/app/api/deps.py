"""Dependências injetáveis com ``Depends``.

O FastAPI resolve as dependências antes de chamar a rota: abre a sessão do banco, lê o
token do cabeçalho, carrega o usuário — e entrega tudo pronto como parâmetros. Nos testes,
qualquer dependência pode ser trocada com ``app.dependency_overrides``.
"""

from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import ler_token
from app.db.session import get_db
from app.models import Usuario

# auto_error=False: nós mesmos respondemos 401 com a mensagem no formato da API.
bearer = HTTPBearer(auto_error=False)


def _nao_autorizado(mensagem: str) -> HTTPException:
    return HTTPException(status.HTTP_401_UNAUTHORIZED, detail=mensagem)


async def get_current_user(
    credenciais: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Usuario:
    if credenciais is None:
        raise _nao_autorizado("Token não informado.")
    try:
        usuario_id = ler_token(credenciais.credentials)
    except jwt.ExpiredSignatureError:
        raise _nao_autorizado("Token expirado.") from None
    except (jwt.PyJWTError, ValueError):
        raise _nao_autorizado("Token inválido.") from None

    usuario = await db.get(Usuario, usuario_id)
    if usuario is None:
        raise _nao_autorizado("Usuário do token não existe mais.")
    return usuario


# Atalhos com Annotated: deixam a assinatura das rotas curta e legível.
DB = Annotated[AsyncSession, Depends(get_db)]
UsuarioAtual = Annotated[Usuario, Depends(get_current_user)]
