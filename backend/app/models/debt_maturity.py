from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosDebtMaturity(Base):
    """Cronograma de vencimentos de divida e covenants.

    Port de db/schema.ts::debtMaturities (Argos legado)."""

    __tablename__ = "argos_debt_maturities"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("argos_companies.id"), nullable=False)
    descricao: Mapped[str] = mapped_column(String, nullable=False)
    vencimento: Mapped[str | None] = mapped_column(String, nullable=True)  # data ou periodo, texto livre
    valor: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    covenant_descricao: Mapped[str | None] = mapped_column(String, nullable=True)
    covenant_status: Mapped[str | None] = mapped_column(String, nullable=True)  # compliant|em_observacao|violado
    fonte: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
