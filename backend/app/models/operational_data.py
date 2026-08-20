from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosOperationalDataPoint(Base):
    """Metricas operacionais setoriais, EAV pelo mesmo motivo de
    ArgosFinancialIndicator (area plantada, capacidade de abate, MW instalado
    etc. variam muito por setor). Port de db/schema.ts::operationalData
    (Argos legado)."""

    __tablename__ = "argos_operational_data"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("argos_companies.id"), nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)
    metric_key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    fonte: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
