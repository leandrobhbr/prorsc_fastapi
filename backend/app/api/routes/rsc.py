"""Rotas da calculadora RSC.

Os parâmetros de cada função dizem ao FastAPI o que fazer:
- ``hashid: str`` aparece no caminho → vem da URL;
- um parâmetro do tipo de um modelo Pydantic → vem do corpo JSON, já validado;
- ``db: DB`` e ``usuario: UsuarioAtual`` → vêm da injeção de dependências.
"""

from fastapi import APIRouter, Depends, status

from app.api.deps import DB, UsuarioAtual, get_current_user
from app.core.hashid import codificar
from app.schemas import saida
from app.schemas.rsc import (
    AtividadeCriada,
    AtividadeEntrada,
    ComCalculos,
    ComCalculosEMensagem,
    CriarRequerimentoEntrada,
    DadosBasicosEntrada,
    ItemCatalogo,
    NivelEntrada,
    NovaAtividadeEntrada,
    RequerimentoCriado,
    RequerimentoDetalhe,
    RequerimentoResumo,
    Sucesso,
)
from app.services import rsc_service

# A dependência no router vale para todas as rotas: sem token válido → 401.
router = APIRouter(
    prefix="/rsc", tags=["Calculadora RSC"], dependencies=[Depends(get_current_user)]
)


@router.get("/catalogo", response_model=dict[str, list[ItemCatalogo]])
async def obter_catalogo(db: DB):
    """Catálogo de itens agrupado por requisito (I a VI)."""
    catalogo = await rsc_service.listar_catalogo(db)
    return {req: [saida.item_catalogo(i) for i in itens] for req, itens in catalogo.items()}


@router.get("", response_model=list[RequerimentoResumo])
async def listar_requerimentos(db: DB, usuario: UsuarioAtual):
    reqs = await rsc_service.listar_requerimentos(db, usuario.id)
    return [saida.requerimento_resumo(r, rsc_service.calcular(r)) for r in reqs]


@router.post("", response_model=RequerimentoCriado, status_code=status.HTTP_201_CREATED)
async def criar_requerimento(dados: CriarRequerimentoEntrada, db: DB, usuario: UsuarioAtual):
    rsc = await rsc_service.criar_requerimento(
        db, usuario, dados.rsc_escolaridade, dados.rsc_nome_servidor
    )
    return {"success": True, "rsc_hashid": codificar("rsc", rsc.rsc_id)}


@router.get("/{hashid}", response_model=RequerimentoDetalhe)
async def obter_dados(hashid: str, db: DB, usuario: UsuarioAtual):
    rsc = await rsc_service.obter_requerimento(db, hashid, usuario.id)
    return saida.requerimento_detalhe(rsc, rsc_service.calcular(rsc))


@router.post("/{hashid}/escolaridade", response_model=ComCalculos)
async def atualizar_dados_basicos(
    hashid: str, dados: DadosBasicosEntrada, db: DB, usuario: UsuarioAtual
):
    rsc = await rsc_service.obter_requerimento(db, hashid, usuario.id)
    calculos = await rsc_service.atualizar_dados_basicos(db, rsc, dados)
    return {"success": True, "calculos": calculos.to_dict()}


@router.post("/{hashid}/nivel-selecionado", response_model=Sucesso)
async def salvar_nivel_selecionado(hashid: str, dados: NivelEntrada, db: DB, usuario: UsuarioAtual):
    rsc = await rsc_service.obter_requerimento(db, hashid, usuario.id)
    await rsc_service.salvar_nivel_selecionado(db, rsc, dados.rsc_nivel_selecionado)
    return {"success": True}


@router.post("/atividade", response_model=AtividadeCriada)
async def adicionar_atividade(dados: NovaAtividadeEntrada, db: DB, usuario: UsuarioAtual):
    ati, calculos = await rsc_service.adicionar_atividade(db, usuario.id, dados)
    return {
        "success": True,
        "message": "Atividade adicionada com sucesso.",
        "rsa_hashid": codificar("atividade", ati.rsa_id),
        "calculos": calculos.to_dict(),
    }


@router.put("/atividade/{hashid}", response_model=ComCalculosEMensagem)
async def atualizar_atividade(hashid: str, dados: AtividadeEntrada, db: DB, usuario: UsuarioAtual):
    ati = await rsc_service.obter_atividade(db, hashid, usuario.id)
    calculos = await rsc_service.atualizar_atividade(db, ati, dados)
    return {
        "success": True,
        "message": "Atividade atualizada com sucesso.",
        "calculos": calculos.to_dict(),
    }


@router.delete("/atividade/{hashid}", response_model=ComCalculosEMensagem)
async def excluir_atividade(hashid: str, db: DB, usuario: UsuarioAtual):
    ati = await rsc_service.obter_atividade(db, hashid, usuario.id)
    calculos = await rsc_service.excluir_atividade(db, ati)
    return {
        "success": True,
        "message": "Atividade removida com sucesso.",
        "calculos": calculos.to_dict(),
    }
