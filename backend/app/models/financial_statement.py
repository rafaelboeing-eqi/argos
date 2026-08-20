from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosFinancialStatement(Base):
    """Uma linha por empresa + periodo + tipo de demonstracao (DRE/BALANCO/
    FLUXO_CAIXA). Campos normalizados cobrem o essencial para credito;
    `raw_json` preserva as demais linhas contabeis sem exigir uma coluna por
    item possivel. Port de db/schema.ts::financialStatements (Argos legado).
    """

    __tablename__ = "argos_financial_statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("argos_companies.id"), nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)  # ex: "2025-Q4" ou "2025"
    period_type: Mapped[str] = mapped_column(String, nullable=False)  # 'trimestral' | 'anual'
    statement_type: Mapped[str] = mapped_column(String, nullable=False)  # 'DRE' | 'BALANCO' | 'FLUXO_CAIXA'
    receita_liquida: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    ebitda: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    lucro_liquido: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    divida_bruta: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    divida_liquida: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    caixa: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    raw_json: Mapped[dict | None] = mapped_column(JSONB(none_as_null=True), nullable=True)
    fonte: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
