"""Converte models em dicionários no formato da API (validados pelo ``response_model``)."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

from app.core.hashid import codificar
from app.domain.calculo import ResultadoCalculo, para_json
from app.models import RscAtividade, RscItemReferencia, RscSaber

FUSO_LOCAL = ZoneInfo("America/Sao_Paulo")


def data_hora_br(valor: datetime | None) -> str | None:
    if valor is None:
        return None
    return valor.replace(tzinfo=UTC).astimezone(FUSO_LOCAL).strftime("%d/%m/%Y %H:%M")


def data_iso(valor: date | None) -> str | None:
    return valor.isoformat() if valor else None


def item_catalogo(item: RscItemReferencia) -> dict:
    return {
        "item_numero": item.rir_numero,
        "item_requisito": item.rir_requisito,
        "item_descricao": item.rir_descricao,
        "item_unidade": item.rir_unidade,
        "item_pontos_unidade": para_json(item.rir_pontos_unidade),
    }


def atividade(ati: RscAtividade) -> dict:
    return {
        "rsa_hashid": codificar("atividade", ati.rsa_id),
        "rsa_requisito": ati.rsa_requisito,
        "rsa_descricao": ati.rsa_descricao,
        "rsa_pontos": para_json(ati.rsa_pontos),
        "rsa_observacoes": ati.rsa_observacoes,
        "rsa_situacao_avaliacao": ati.rsa_situacao_avaliacao,
    }


def requerimento_resumo(rsc: RscSaber, calculos: ResultadoCalculo) -> dict:
    return {
        "rsc_hashid": codificar("rsc", rsc.rsc_id),
        "rsc_status": rsc.rsc_status,
        "rsc_escolaridade": rsc.rsc_escolaridade,
        "rsc_nivel_selecionado": rsc.rsc_nivel_selecionado,
        "atividades_count": len(rsc.atividades),
        "total_pontos": para_json(calculos.total_pontos),
        "melhor_nivel": calculos.melhor_nivel,
        "created_at": data_hora_br(rsc.created_at),
        "updated_at": data_hora_br(rsc.updated_at),
    }


def requerimento_detalhe(rsc: RscSaber, calculos: ResultadoCalculo) -> dict:
    return {
        "rsc_hashid": codificar("rsc", rsc.rsc_id),
        "rsc_status": rsc.rsc_status,
        "rsc_escolaridade": rsc.rsc_escolaridade,
        "rsc_nome_servidor": rsc.rsc_nome_servidor,
        "rsc_nivel_selecionado": rsc.rsc_nivel_selecionado,
        "rsc_data_ultima_concessao": data_iso(rsc.rsc_data_ultima_concessao),
        "atividades": [atividade(a) for a in rsc.atividades],
        "calculos": calculos.to_dict(),
    }
