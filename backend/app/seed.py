"""Carga inicial: catálogo RSC e usuários de demonstração.

Uso:  uv run python -m app.seed
"""

import asyncio
import json
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import gerar_hash_senha
from app.db.session import SessionLocal
from app.models import RscItemReferencia, Usuario

CATALOGO_JSON = Path(__file__).parent / "data" / "catalogo_rsc.json"

USUARIOS_DEMO = [
    ("Servidor Demonstração", "teste@teste.com.br", "123456"),
    ("Outro Servidor", "outro@prorsctae.local", "outro123"),
]


async def semear_catalogo(db: AsyncSession) -> int:
    """Insere ou atualiza os itens do catálogo (pode rodar várias vezes)."""
    itens = json.loads(CATALOGO_JSON.read_text(encoding="utf-8"))
    existentes = {i.rir_numero: i for i in await db.scalars(select(RscItemReferencia))}
    for dado in itens:
        item = existentes.get(dado["numero"]) or RscItemReferencia(rir_numero=dado["numero"])
        item.rir_requisito = dado["requisito"]
        item.rir_descricao = dado["descricao"]
        item.rir_unidade = dado["unidade"]
        item.rir_pontos_unidade = Decimal(str(dado["pontos_unidade"]))
        item.rir_ativo = "S"
        db.add(item)
    await db.commit()
    return len(itens)


async def semear_usuarios(db: AsyncSession) -> list[str]:
    criados = []
    for nome, email, senha in USUARIOS_DEMO:
        if await db.scalar(select(Usuario).where(Usuario.email == email)) is None:
            db.add(Usuario(name=nome, email=email, password=gerar_hash_senha(senha)))
            criados.append(email)
    await db.commit()
    return criados


async def main() -> None:
    async with SessionLocal() as db:
        print(f"Catálogo: {await semear_catalogo(db)} itens.")
        for email in await semear_usuarios(db):
            print(f"Usuário criado: {email}")


if __name__ == "__main__":
    asyncio.run(main())
