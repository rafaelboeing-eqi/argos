from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosSectorFrameworkMetric(Base):
    """O framework de cada especialista setorial e DADO, nao apenas prompt.
    `company_id` nulo = metrica default do setor; preenchido = especifica da
    empresa. `status='proposed'` = especialista sugeriu, aguarda revisao
    humana antes de virar 'active' - a promocao e sempre uma acao humana
    explicita, nunca automatica.

    Port de db/schema.ts::sectorFrameworks (Argos legado).
    """

    __tablename__ = "argos_sector_frameworks"

    id: Mapped[int] = mapped_column(primary_key=True)
    setor: Mapped[str] = mapped_column(String, nullable=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("argos_companies.id"), nullable=True)
    metric_key: Mapped[str] = mapped_column(String, nullable=False)
    relevancia_credito: Mapped[str] = mapped_column(Text, nullable=False)
    como_interpretar: Mapped[str] = mapped_column(Text, nullable=False)
    sinal_melhora: Mapped[str] = mapped_column(Text, nullable=False)
    sinal_deterioracao: Mapped[str] = mapped_column(Text, nullable=False)
    fonte_ideal: Mapped[str] = mapped_column(String, nullable=False)
    frequencia_atualizacao: Mapped[str] = mapped_column(String, nullable=False)
    prioridade: Mapped[str] = mapped_column(String, nullable=False)  # Essencial|Relevante|Complementar
    status: Mapped[str] = mapped_column(String, nullable=False, default="proposed", server_default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
