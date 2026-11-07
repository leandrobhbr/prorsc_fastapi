from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Classe base dos models (SQLAlchemy 2.0, estilo ``Mapped[...]``)."""


def agora_utc() -> datetime:
    """Datas gravadas em UTC (sem fuso) e convertidas para o horário local ao exibir."""
    return datetime.now(UTC).replace(tzinfo=None)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=agora_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=agora_utc, onupdate=agora_utc)
