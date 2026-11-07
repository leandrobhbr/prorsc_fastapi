from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, SmallInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class RscSaber(TimestampMixin, Base):
    """Requerimento (cálculo) RSC-TAE de um servidor."""

    __tablename__ = "tb_rsc_saberes"

    rsc_id: Mapped[int] = mapped_column(primary_key=True)
    usu_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    rsc_escolaridade: Mapped[str] = mapped_column(String(30))
    rsc_nome_servidor: Mapped[str | None] = mapped_column(String(200))
    rsc_nivel_selecionado: Mapped[str | None] = mapped_column(String(10))
    rsc_data_ultima_concessao: Mapped[date | None] = mapped_column(Date)
    rsc_status: Mapped[str] = mapped_column(String(20), default="rascunho", index=True)

    # lazy="selectin": as atividades são carregadas junto, em uma consulta extra.
    # No modo async não existe carregamento "preguiçoso" ao acessar o atributo.
    atividades: Mapped[list["RscAtividade"]] = relationship(
        back_populates="requerimento",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="(RscAtividade.rsa_requisito, RscAtividade.created_at, RscAtividade.rsa_id)",
    )


class RscAtividade(TimestampMixin, Base):
    """Atividade declarada em um requerimento, ligada a um requisito (I a VI)."""

    __tablename__ = "tb_rsc_atividades"

    rsa_id: Mapped[int] = mapped_column(primary_key=True)
    rsc_id: Mapped[int] = mapped_column(
        ForeignKey("tb_rsc_saberes.rsc_id", ondelete="CASCADE"), index=True
    )
    rsa_requisito: Mapped[str] = mapped_column(String(5))
    rsa_descricao: Mapped[str] = mapped_column(Text)
    rsa_pontos: Mapped[Decimal] = mapped_column(Numeric(8, 2))
    rsa_observacoes: Mapped[str | None] = mapped_column(Text)
    rsa_situacao_avaliacao: Mapped[str | None] = mapped_column(String(30))

    # lazy="raise": acessar sem ter carregado antes (com selectinload) gera erro imediato,
    # em vez de uma consulta escondida — o que no modo async nem é possível.
    requerimento: Mapped[RscSaber] = relationship(back_populates="atividades", lazy="raise")


class RscItemReferencia(TimestampMixin, Base):
    """Catálogo (rol) de saberes e competências — Anexos I a VI."""

    __tablename__ = "tb_rsc_itens_referencia"

    rir_id: Mapped[int] = mapped_column(primary_key=True)
    rir_numero: Mapped[int] = mapped_column(SmallInteger, unique=True)
    rir_requisito: Mapped[str] = mapped_column(String(5), index=True)
    rir_descricao: Mapped[str] = mapped_column(Text)
    rir_unidade: Mapped[str] = mapped_column(String(100))
    rir_pontos_unidade: Mapped[Decimal] = mapped_column(Numeric(8, 4))
    rir_ativo: Mapped[str] = mapped_column(String(1), default="S")
