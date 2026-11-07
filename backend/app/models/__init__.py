"""Models (tabelas). Nomes de tabelas e colunas seguem o schema original do ProRSC-TAE."""

from app.models.rsc import RscAtividade, RscItemReferencia, RscSaber
from app.models.usuario import Usuario

__all__ = ["RscAtividade", "RscItemReferencia", "RscSaber", "Usuario"]
