"""Schemas Pydantic: o FastAPI usa os tipos para validar a entrada, converter e documentar.

- Entrada: o corpo JSON é validado contra a classe declarada como parâmetro da rota.
- Saída: ``response_model`` filtra e documenta a resposta no OpenAPI (``/docs``).
"""

from datetime import date
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Escolaridade = Literal[
    "fund_incompleto", "fund_completo", "medio", "graduacao", "especializacao", "mestrado",
    "doutorado",
]  # fmt: skip
Nivel = Literal["RSC-I", "RSC-II", "RSC-III", "RSC-IV", "RSC-V", "RSC-VI"]
Requisito = Literal["I", "II", "III", "IV", "V", "VI"]
Numero = int | float


class Entrada(BaseModel):
    model_config = ConfigDict(extra="ignore")

    @model_validator(mode="before")
    @classmethod
    def remover_vazios(cls, dados: Any) -> Any:
        """Texto vazio ou null equivalem a "não informado": o campo usa o padrão (ou falta)."""
        if isinstance(dados, dict):
            return {k: v for k, v in dados.items() if v not in ("", None)}
        return dados


# ─── Entrada ─────────────────────────────────────────────────────────────────


class LoginEntrada(BaseModel):
    # Opcionais de propósito: campos ausentes respondem 401 com mensagem própria, não 422.
    email: str | None = None
    password: str | None = None


class CriarRequerimentoEntrada(Entrada):
    rsc_escolaridade: Escolaridade | None = None
    rsc_nome_servidor: str | None = Field(default=None, max_length=200)


class DadosBasicosEntrada(Entrada):
    rsc_escolaridade: Escolaridade
    rsc_nome_servidor: str | None = Field(default=None, max_length=200)
    rsc_data_ultima_concessao: date | None = None


class NivelEntrada(Entrada):
    rsc_nivel_selecionado: Nivel


class AtividadeEntrada(Entrada):
    rsa_requisito: Requisito
    rsa_descricao: str = Field(max_length=1000)
    rsa_pontos: Decimal = Field(ge=0, le=9999)
    rsa_observacoes: str | None = Field(default=None, max_length=2000)


class NovaAtividadeEntrada(AtividadeEntrada):
    rsc_hashid: str


#: Mensagens em português por campo e por tipo de erro do Pydantic.
#: Usadas pelo handler de validação em ``app/errors.py``.
MENSAGENS_VALIDACAO: dict[str, dict[str, str]] = {
    "rsc_escolaridade": {
        "missing": "A escolaridade é obrigatória.",
        "literal_error": "Escolaridade inválida.",
    },
    "rsc_nivel_selecionado": {
        "missing": "O nível é obrigatório.",
        "literal_error": "Nível RSC inválido.",
    },
    "rsa_requisito": {
        "missing": "O requisito é obrigatório.",
        "literal_error": "Requisito inválido. Use I, II, III, IV, V ou VI.",
    },
    "rsa_descricao": {
        "missing": "A descrição é obrigatória.",
        "string_too_long": "A descrição deve ter no máximo 1000 caracteres.",
    },
    "rsa_pontos": {
        "missing": "A pontuação é obrigatória.",
        "decimal_parsing": "A pontuação deve ser um número.",
        "decimal_type": "A pontuação deve ser um número.",
        "greater_than_equal": "A pontuação deve estar entre 0 e 9999.",
        "less_than_equal": "A pontuação deve estar entre 0 e 9999.",
    },
    "rsc_hashid": {"missing": "O requerimento é obrigatório."},
    "rsc_data_ultima_concessao": {
        "date_from_datetime_parsing": "Data inválida.",
        "date_parsing": "Data inválida.",
    },
}


# ─── Saída ───────────────────────────────────────────────────────────────────


class LoginSaida(BaseModel):
    success: bool
    token: str
    name: str
    email: str
    usu_hashid: str


class ItemCatalogo(BaseModel):
    item_numero: int
    item_requisito: Requisito
    item_descricao: str
    item_unidade: str
    item_pontos_unidade: Numero


class StatusNivel(BaseModel):
    nivel: Nivel
    label: str
    label_curto: str
    equivalente: str
    atencao: str
    pontos_minimos: int
    criterios_minimos: int
    req_obrigatorio: list[Requisito]
    disponivel: bool
    atingido: bool
    req_obrigatorio_ok: bool
    pontos_restantes: Numero
    criterios_restantes: int


class Calculos(BaseModel):
    total_pontos: Numero
    total_criterios: int
    pontos_por_requisito: dict[Requisito, Numero]
    criterios_por_requisito: dict[Requisito, int]
    niveis: dict[Nivel, StatusNivel]
    melhor_nivel: Nivel | None
    proximo_nivel: Nivel | None


class RequerimentoResumo(BaseModel):
    rsc_hashid: str
    rsc_status: str
    rsc_escolaridade: str
    rsc_nivel_selecionado: str | None
    atividades_count: int
    total_pontos: Numero
    melhor_nivel: Nivel | None
    created_at: str | None
    updated_at: str | None


class Atividade(BaseModel):
    rsa_hashid: str
    rsa_requisito: Requisito
    rsa_descricao: str
    rsa_pontos: Numero
    rsa_observacoes: str | None
    rsa_situacao_avaliacao: str | None


class RequerimentoDetalhe(BaseModel):
    rsc_hashid: str
    rsc_status: str
    rsc_escolaridade: str
    rsc_nome_servidor: str | None
    rsc_nivel_selecionado: str | None
    rsc_data_ultima_concessao: str | None
    atividades: list[Atividade]
    calculos: Calculos


class Sucesso(BaseModel):
    success: bool = True


class RequerimentoCriado(Sucesso):
    rsc_hashid: str


class ComCalculos(Sucesso):
    calculos: Calculos


class ComCalculosEMensagem(ComCalculos):
    message: str


class AtividadeCriada(ComCalculosEMensagem):
    rsa_hashid: str
