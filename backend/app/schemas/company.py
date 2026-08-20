from datetime import datetime
from typing import Literal

from pydantic import BaseModel

# Port 1:1 dos schemas de entrada de routes/companies.ts (Argos legado).


class CompanyCreate(BaseModel):
    nome: str
    cnpj: str | None = None
    ticker: str | None = None
    setor: str
    grupo_economico: str | None = None


class Company(BaseModel):
    id: int
    nome: str
    cnpj: str | None
    ticker: str | None
    setor: str
    grupo_economico: str | None
    created_at: datetime


class FinancialStatementInput(BaseModel):
    statement_type: Literal["DRE", "BALANCO", "FLUXO_CAIXA"]
    receita_liquida: float | None = None
    ebitda: float | None = None
    lucro_liquido: float | None = None
    divida_bruta: float | None = None
    divida_liquida: float | None = None
    caixa: float | None = None
    raw_json: dict | None = None
    fonte: str | None = None


class FinancialIndicatorInput(BaseModel):
    metric_key: str
    value: float | None = None
    unit: str | None = None
    fonte: str | None = None


class OperationalDataInput(BaseModel):
    metric_key: str
    value: float | None = None
    unit: str | None = None
    fonte: str | None = None


class DebtMaturityInput(BaseModel):
    descricao: str
    vencimento: str | None = None
    valor: float | None = None
    covenant_descricao: str | None = None
    covenant_status: Literal["compliant", "em_observacao", "violado"] | None = None
    fonte: str | None = None


class TriggerAnalysisRequest(BaseModel):
    period: str | None = None


class IngestPeriodRequest(BaseModel):
    """Ingestao manual/mock de um novo periodo - o cenario-alvo desta fase,
    ja que ainda nao ha integracao com uma fonte real (CVM, sistema interno
    etc.)."""

    period: str
    period_type: Literal["trimestral", "anual"]
    statements: list[FinancialStatementInput] = []
    indicators: list[FinancialIndicatorInput] = []
    operational_data: list[OperationalDataInput] = []
    debt_maturities: list[DebtMaturityInput] = []
    dispara_analise: bool = True
