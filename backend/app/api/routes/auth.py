import re

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.api.deps import DB
from app.core.hashid import codificar
from app.core.security import criar_token, senha_confere
from app.models import Usuario
from app.schemas.rsc import LoginEntrada, LoginSaida

router = APIRouter(tags=["Autenticação"])

_RE_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _falha(mensagem: str) -> JSONResponse:
    return JSONResponse({"success": False, "message": mensagem}, status_code=401)


@router.post(
    "/login",
    response_model=LoginSaida,
    responses={401: {"description": "E-mail ou senha inválidos"}},
)
async def login(dados: LoginEntrada, db: DB):
    """Autentica com e-mail e senha e devolve um token JWT."""
    email = (dados.email or "").strip()
    if not email or not dados.password:
        return _falha("E-mail e senha são obrigatórios.")
    if not _RE_EMAIL.match(email):
        return _falha("E-mail inválido.")

    usuario = await db.scalar(select(Usuario).where(Usuario.email == email))
    if usuario is None or not senha_confere(dados.password, usuario.password):
        # Mensagem única: não revela se o e-mail existe.
        return _falha("E-mail ou senha inválidos.")

    return {
        "success": True,
        "token": criar_token(usuario.id),
        "name": usuario.name,
        "email": usuario.email,
        "usu_hashid": codificar("usuario", usuario.id),
    }
