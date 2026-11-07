"""Ambiente do Alembic (migrations), versão assíncrona.

- A URL do banco vem das configurações da aplicação (``DATABASE_URL``), não do alembic.ini.
- ``target_metadata`` aponta para os models: é o que permite o ``--autogenerate``.
- ``render_as_batch=True``: no SQLite, alterações de coluna recriam a tabela (batch mode).
"""

import asyncio
from logging.config import fileConfig

from sqlalchemy.engine import Connection

import app.models  # noqa: F401  (registra as tabelas no metadata)
from alembic import context
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import criar_engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
URL = get_settings().database_url


def run_migrations_offline() -> None:
    """Gera o SQL sem conectar no banco (``alembic upgrade head --sql``)."""
    context.configure(
        url=URL,
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def _executar(conexao: Connection) -> None:
    context.configure(connection=conexao, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = criar_engine(URL)
    async with engine.connect() as conexao:
        # O Alembic é síncrono: run_sync executa-o dentro da conexão assíncrona.
        await conexao.run_sync(_executar)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
