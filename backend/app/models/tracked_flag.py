from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosTrackedFlag(Base):
    """Memoria analitica: red flags e pontos de atencao rastreados ao longo
    de analises sucessivas, com status evolutivo (aberto -> confirmado ->
    revertido / resolvido). E o Flag Tracker.

    Port de db/schema.ts::trackedFlags (Argos legado).
    """

    __tablename__ = "argos_tracked_flags"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("argos_companies.id"), nullable=False)
    categoria: Mapped[str] = mapped_column(String, nullable=False)  # ponto_atencao | red_flag
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    first_seen_analysis_id: Mapped[int] = mapped_column(ForeignKey("argos_analyses.id"), nullable=False)
    last_seen_analysis_id: Mapped[int] = mapped_column(ForeignKey("argos_analyses.id"), nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="aberto", server_default="aberto")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
