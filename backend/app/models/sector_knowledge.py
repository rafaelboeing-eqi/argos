from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosSectorKnowledge(Base):
    """Conhecimento setorial (app/schemas/sector_knowledge.py), separado do
    framework de metricas: modelo de negocio, drivers, riscos, relacoes
    causais, red flags, contexto externo e monitoramento de cada setor. Evolui
    independentemente do framework (sem a governanca proposed -> active ->
    deprecated - e conteudo interpretativo, nao uma metrica oficial
    monitorada) e sem exigir alteracao de codigo: uma nova linha aqui ja
    habilita um novo especialista setorial.

    `content` guarda o corpo de SectorKnowledge sem o campo `setor` (ja e
    coluna), como JSONB nativo do Postgres (o legado usava TEXT com
    JSON.stringify por limitacao do SQLite).

    Port de db/schema.ts::sectorKnowledge (Argos legado).
    """

    __tablename__ = "argos_sector_knowledge"

    id: Mapped[int] = mapped_column(primary_key=True)
    setor: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
