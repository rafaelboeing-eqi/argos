from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosSectorAgentRun(Base):
    """Saida bruta do especialista setorial por analise, para auditoria do
    cruzamento setorial feito pelo Master.

    Port de db/schema.ts::sectorAgentRuns (Argos legado).
    """

    __tablename__ = "argos_sector_agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    analysis_id: Mapped[int] = mapped_column(ForeignKey("argos_analyses.id"), nullable=False)
    setor: Mapped[str] = mapped_column(String, nullable=False)
    raw_output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
