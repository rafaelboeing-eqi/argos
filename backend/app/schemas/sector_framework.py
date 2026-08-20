from typing import Literal

from pydantic import BaseModel

# Port 1:1 de schemas/sectorFramework.ts (Argos legado).
SectorMetricPriority = Literal["Essencial", "Relevante", "Complementar"]
SectorFrameworkStatus = Literal["active", "proposed", "deprecated"]


class SectorMetricDefinition(BaseModel):
    setor: str
    company_id: int | None = None  # None = default do setor; preenchido = especifico da empresa
    metric_key: str
    relevancia_credito: str
    como_interpretar: str
    sinal_melhora: str
    sinal_deterioracao: str
    fonte_ideal: str
    frequencia_atualizacao: str
    prioridade: SectorMetricPriority


class SectorFramework(BaseModel):
    """Framework completo de um setor: o menor conjunto de metricas capaz de
    explicar os principais riscos de credito daquele setor."""

    setor: str
    metricas: list[SectorMetricDefinition]
