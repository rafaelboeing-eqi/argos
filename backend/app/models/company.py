from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosCompany(Base):
    """Empresa cadastrada para analise de credito.

    `setor` e atribuido no cadastro (nao inferido por NLP) - o Master de
    Credito le este campo em vez de tentar classificar o setor sozinho.
    Port de db/schema.ts::companies (Argos legado).
    """

    __tablename__ = "argos_companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String, nullable=False)
    cnpj: Mapped[str | None] = mapped_column(String, nullable=True)
    ticker: Mapped[str | None] = mapped_column(String, nullable=True)
    setor: Mapped[str] = mapped_column(String, nullable=False)
    grupo_economico: Mapped[str | None] = mapped_column("grupo_economico", String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
