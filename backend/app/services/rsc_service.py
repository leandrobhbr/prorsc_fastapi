"""Casos de uso da calculadora RSC (versão assíncrona).

Cada função recebe a sessão do banco (``AsyncSession``) como parâmetro — ela vem da
injeção de dependências do FastAPI. Toda ida ao banco usa ``await``: enquanto espera o
banco, o servidor atende outras requisições no mesmo processo.
"""

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.hashid import decodificar
from app.domain import calculo
from app.models import RscAtividade, RscItemReferencia, RscSaber, Usuario
from app.schemas.rsc import AtividadeEntrada, DadosBasicosEntrada, NovaAtividadeEntrada
from app.services.excecoes import AcessoNegado, NaoEncontrado, RegraNegocio


def calcular(rsc: RscSaber) -> calculo.ResultadoCalculo:
    atividades = [
        calculo.AtividadeCalculo(a.rsa_requisito, a.rsa_pontos, a.rsa_situacao_avaliacao)
        for a in rsc.atividades
    ]
    return calculo.calcular(atividades, rsc.rsc_escolaridade)


async def listar_catalogo(db: AsyncSession) -> dict[str, list[RscItemReferencia]]:
    itens = await db.scalars(
        select(RscItemReferencia)
        .where(RscItemReferencia.rir_ativo == "S")
        .order_by(RscItemReferencia.rir_requisito, RscItemReferencia.rir_numero)
    )
    agrupado: dict[str, list[RscItemReferencia]] = defaultdict(list)
    for item in itens:
        agrupado[item.rir_requisito].append(item)
    return dict(agrupado)


async def listar_requerimentos(db: AsyncSession, usu_id: int) -> list[RscSaber]:
    # As atividades vêm junto em UMA consulta extra (lazy="selectin" no model): sem N+1.
    resultado = await db.scalars(
        select(RscSaber)
        .where(RscSaber.usu_id == usu_id)
        .order_by(RscSaber.created_at.desc(), RscSaber.rsc_id.desc())
    )
    return list(resultado)


async def criar_requerimento(
    db: AsyncSession, usuario: Usuario, escolaridade: str | None, nome: str | None
) -> RscSaber:
    rsc = RscSaber(
        usu_id=usuario.id,
        rsc_escolaridade=escolaridade or "graduacao",
        rsc_nome_servidor=nome or usuario.name,
        rsc_status="rascunho",
        atividades=[],
    )
    db.add(rsc)
    await db.commit()
    return rsc


async def obter_requerimento(db: AsyncSession, hashid: str, usu_id: int) -> RscSaber:
    rsc_id = decodificar("rsc", hashid)
    rsc = await db.get(RscSaber, rsc_id) if rsc_id else None
    if rsc is None:
        raise NaoEncontrado("Requerimento não encontrado.", como_lista=False)
    if rsc.usu_id != usu_id:
        raise AcessoNegado("Acesso negado.", como_lista=False)
    return rsc


def garantir_editavel(rsc: RscSaber) -> None:
    if not calculo.status_editavel(rsc.rsc_status):
        raise RegraNegocio(
            f'O requerimento não pode ser editado no status atual ("{rsc.rsc_status}").'
        )


async def atualizar_dados_basicos(
    db: AsyncSession, rsc: RscSaber, dados: DadosBasicosEntrada
) -> calculo.ResultadoCalculo:
    garantir_editavel(rsc)
    rsc.rsc_escolaridade = dados.rsc_escolaridade
    rsc.rsc_nome_servidor = dados.rsc_nome_servidor
    rsc.rsc_data_ultima_concessao = dados.rsc_data_ultima_concessao
    await db.commit()
    return calcular(rsc)


async def salvar_nivel_selecionado(db: AsyncSession, rsc: RscSaber, nivel: str) -> None:
    garantir_editavel(rsc)
    erro = calculo.validar_nivel_selecionado(nivel, rsc.rsc_escolaridade)
    if erro:
        raise RegraNegocio(erro)
    rsc.rsc_nivel_selecionado = nivel
    await db.commit()


async def obter_atividade(db: AsyncSession, hashid: str, usu_id: int) -> RscAtividade:
    rsa_id = decodificar("atividade", hashid)
    # Carrega explicitamente atividade → requerimento → todas as atividades do requerimento,
    # que serão usadas no recálculo. Em modo async, o que não for carregado aqui não pode
    # ser buscado depois "sob demanda" (o model usa lazy="raise" para acusar isso cedo).
    ati = (
        await db.scalar(
            select(RscAtividade)
            .where(RscAtividade.rsa_id == rsa_id)
            .options(selectinload(RscAtividade.requerimento).selectinload(RscSaber.atividades))
        )
        if rsa_id
        else None
    )
    if ati is None or ati.requerimento.usu_id != usu_id:
        raise NaoEncontrado("Atividade não encontrada.")
    return ati


async def _garantir_item_nao_duplicado(
    db: AsyncSession, rsc: RscSaber, requisito: str, observacoes: str | None
) -> None:
    numero = calculo.numero_item_catalogo(observacoes)
    if numero is None:
        return
    existe = await db.scalar(
        select(RscAtividade.rsa_id).where(
            RscAtividade.rsc_id == rsc.rsc_id,
            RscAtividade.rsa_requisito == requisito,
            RscAtividade.rsa_observacoes.like(f"Item nº {numero} %"),
        )
    )
    if existe:
        raise RegraNegocio("Este item já foi adicionado neste requisito.")


async def adicionar_atividade(
    db: AsyncSession, usu_id: int, dados: NovaAtividadeEntrada
) -> tuple[RscAtividade, calculo.ResultadoCalculo]:
    rsc = await obter_requerimento(db, dados.rsc_hashid, usu_id)
    garantir_editavel(rsc)
    await _garantir_item_nao_duplicado(db, rsc, dados.rsa_requisito, dados.rsa_observacoes)

    ati = RscAtividade(
        rsa_requisito=dados.rsa_requisito,
        rsa_descricao=dados.rsa_descricao,
        rsa_pontos=dados.rsa_pontos,
        rsa_observacoes=dados.rsa_observacoes,
    )
    rsc.atividades.append(ati)
    await db.commit()
    return ati, calcular(rsc)


async def atualizar_atividade(
    db: AsyncSession, ati: RscAtividade, dados: AtividadeEntrada
) -> calculo.ResultadoCalculo:
    garantir_editavel(ati.requerimento)
    ati.rsa_requisito = dados.rsa_requisito
    ati.rsa_descricao = dados.rsa_descricao
    ati.rsa_pontos = dados.rsa_pontos
    ati.rsa_observacoes = dados.rsa_observacoes
    await db.commit()
    return calcular(ati.requerimento)


async def excluir_atividade(db: AsyncSession, ati: RscAtividade) -> calculo.ResultadoCalculo:
    rsc = ati.requerimento
    garantir_editavel(rsc)
    rsc.atividades.remove(ati)  # delete-orphan: sai da lista = apagada do banco
    await db.commit()
    return calcular(rsc)
