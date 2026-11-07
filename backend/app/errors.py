"""Tradução de exceções em respostas JSON no formato que o frontend espera.

- 401/403/404 (HTTPException): ``{"message": "..."}``
- 422 de validação: ``{"message": "...", "errors": {"campo": ["mensagem"]}}``
  (o padrão do FastAPI seria ``{"detail": [...]}`` em inglês; aqui adaptamos)
- 422 de regra de negócio: ``{"errors": ["mensagem"]}``
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.schemas.rsc import MENSAGENS_VALIDACAO
from app.services.excecoes import ErroAplicacao

_MENSAGENS_GENERICAS = {
    "missing": "Campo obrigatório.",
    "json_invalid": "JSON inválido.",
}


def _mensagem(erro: dict) -> str:
    campo = str(erro["loc"][-1])
    tipo = erro["type"]
    por_campo = MENSAGENS_VALIDACAO.get(campo, {})
    if tipo in por_campo:
        return por_campo[tipo]
    if tipo == "string_too_long":
        return f"Máximo de {erro['ctx']['max_length']} caracteres."
    return _MENSAGENS_GENERICAS.get(tipo, erro["msg"])


def registrar_handlers(app: FastAPI) -> None:
    @app.exception_handler(ErroAplicacao)
    async def erro_aplicacao(_request: Request, exc: ErroAplicacao):
        return JSONResponse(exc.to_dict(), status_code=exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def erro_validacao(_request: Request, exc: RequestValidationError):
        erros: dict[str, list[str]] = {}
        for erro in exc.errors():
            # loc = ("body", "rsa_pontos"): o último elemento é o nome do campo.
            campo = str(erro["loc"][-1]) if len(erro["loc"]) > 1 else "body"
            erros.setdefault(campo, []).append(_mensagem(erro))
        return JSONResponse(
            {"message": "Os dados informados são inválidos.", "errors": erros}, status_code=422
        )

    @app.exception_handler(StarletteHTTPException)
    async def erro_http(_request: Request, exc: StarletteHTTPException):
        return JSONResponse({"message": exc.detail}, status_code=exc.status_code)
