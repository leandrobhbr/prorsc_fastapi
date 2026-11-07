"""Conexão assíncrona com o banco (SQLAlchemy 2.0 async + aiosqlite).

- ``engine``: o pool de conexões.
- ``SessionLocal``: fábrica de sessões (uma sessão = uma "unidade de trabalho").
- ``get_db``: dependência do FastAPI que abre uma sessão por requisição e a fecha no final.
"""

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def criar_engine(url: str):
    if url.startswith("sqlite") and ":///" in url and ":memory:" not in url:
        # Garante que a pasta do arquivo .db exista.
        Path(url.split(":///", 1)[1]).parent.mkdir(parents=True, exist_ok=True)

    engine = create_async_engine(url)

    if url.startswith("sqlite"):
        # Eventos de conexão são síncronos: ficam no "sync_engine" por trás do async.
        @event.listens_for(engine.sync_engine, "connect")
        def _pragmas(conexao, _registro):
            cursor = conexao.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")  # o SQLite vem com FKs desligadas
            cursor.execute("PRAGMA journal_mode=WAL")  # leituras em paralelo com escrita
            cursor.close()

    return engine


engine = criar_engine(get_settings().database_url)

# expire_on_commit=False: os objetos continuam utilizáveis depois do commit. Em modo async
# isso é essencial, porque recarregar atributos "sob demanda" (lazy load) não é permitido.
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as sessao:
        yield sessao
