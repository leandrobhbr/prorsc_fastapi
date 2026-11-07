from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Usuario(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password: Mapped[str] = mapped_column(String(255))  # hash bcrypt
