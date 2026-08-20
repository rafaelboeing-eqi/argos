from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosCreditAnalysis(Base):
    """Uma linha por rodada de analise do Master de Credito. `output` e o
    JSON completo validado por app.schemas.credit_analysis.AnalysisOutput
    (as 14 secoes), guardado como JSONB nativo.

    Port de db/schema.ts::analyses (Argos legado).
    """

    __tablename__ = "argos_analyses"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("argos_companies.id"), nullable=False)
    period: Mapped[str] = mapped_column(String, nullable=False)
    output: Mapped[dict] = mapped_column(JSONB, nullable=False)
    tendencia: Mapped[str] = mapped_column(String, nullable=False)  # melhora|estavel|deteriorando
    risco_credito: Mapped[str] = mapped_column(String, nullable=False)  # baixo|moderado|elevado|critico
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
