"""Fixtures: banco SQLite em memória, app com a dependência ``get_db`` trocada e cliente HTTP."""

import os

# Configuração de teste ANTES de importar a aplicação (Settings lê o ambiente).
os.environ.update(
    DATABASE_URL="sqlite+aiosqlite:///:memory:",
    JWT_SECRET="segredo-de-teste-com-pelo-menos-32-bytes",
    HASHIDS_SALT="salt-de-teste",
    BCRYPT_ROUNDS="4",
)

import pytest  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app as aplicacao  # noqa: E402
from app.seed import semear_catalogo, semear_usuarios  # noqa: E402


@pytest.fixture
async def sessao_fabrica():
    # StaticPool: uma única conexão compartilhada, senão cada conexão veria um banco vazio.
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    fabrica = async_sessionmaker(engine, expire_on_commit=False)
    async with fabrica() as db:
        await semear_catalogo(db)
        await semear_usuarios(db)
    yield fabrica
    await engine.dispose()


@pytest.fixture
async def db(sessao_fabrica):
    async with sessao_fabrica() as sessao:
        yield sessao


@pytest.fixture
async def client(sessao_fabrica):
    async def get_db_teste():
        async with sessao_fabrica() as sessao:
            yield sessao

    # Troca a dependência real pela de teste — recurso nativo do FastAPI.
    aplicacao.dependency_overrides[get_db] = get_db_teste
    transporte = ASGITransport(app=aplicacao)
    async with AsyncClient(transport=transporte, base_url="http://teste") as cliente:
        yield cliente
    aplicacao.dependency_overrides.clear()


async def _token(client, email: str, senha: str) -> dict[str, str]:
    resp = await client.post("/api/v1/login", json={"email": email, "password": senha})
    assert resp.status_code == 200, resp.json()
    return {"Authorization": f"Bearer {resp.json()['token']}"}


@pytest.fixture
async def auth(client):
    return await _token(client, "teste@teste.com.br", "123456")


@pytest.fixture
async def auth_outro(client):
    return await _token(client, "outro@prorsctae.local", "outro123")


@pytest.fixture
async def rsc_hashid(client, auth):
    resp = await client.post("/api/v1/rsc", json={"rsc_escolaridade": "graduacao"}, headers=auth)
    assert resp.status_code == 201
    return resp.json()["rsc_hashid"]
