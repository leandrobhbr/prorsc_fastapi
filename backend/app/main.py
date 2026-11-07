# Calculadora RSC-TAE de livre acesso — derivada do ProRSC-TAE (Software Público Brasileiro).
# Licenciado sob a GNU General Public License v2.0 ou posterior (GPL-2.0-or-later).
"""Aplicação FastAPI.

Rodar em desenvolvimento:  uv run uvicorn app.main:app --reload --port 8002
Documentação automática:   http://localhost:8002/docs
"""

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, rsc
from app.core.config import get_settings
from app.errors import registrar_handlers


def create_app() -> FastAPI:
    app = FastAPI(
        title="Calculadora RSC-TAE",
        description="API da calculadora de Reconhecimento de Saberes e Competências (RSC-TAE).",
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        root_path=get_settings().root_path,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=get_settings().lista_cors,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    registrar_handlers(app)

    api_v1 = APIRouter(prefix="/api/v1")
    api_v1.include_router(auth.router)
    api_v1.include_router(rsc.router)

    @api_v1.get("/health", tags=["Infra"])
    async def health():
        return {"status": "ok"}

    app.include_router(api_v1)
    return app


app = create_app()
