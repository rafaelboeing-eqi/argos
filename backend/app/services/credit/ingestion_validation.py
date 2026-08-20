"""Regras de integridade dos dados de entrada do dominio de credito, checadas
antes da persistencia na ingestao manual/mock de periodo (POST
/companies/{id}/financial-periods). Sao regras sobre o formato/plausibilidade
do que entra - nunca sobre risco de credito, que continua sendo julgamento
exclusivo do Master Agent (ver services/credit/master_agent.py).
"""

import re

from app.schemas.company import IngestPeriodRequest

_PERIOD_ANUAL = re.compile(r"^\d{4}$")
_PERIOD_TRIMESTRAL = re.compile(r"^\d{4}-Q[1-4]$")


class IngestValidationError(ValueError):
    def __init__(self, erros: list[str]):
        self.erros = erros
        super().__init__("; ".join(erros))


def validate_ingest_period(payload: IngestPeriodRequest) -> None:
    erros: list[str] = []

    if payload.period_type == "anual" and not _PERIOD_ANUAL.match(payload.period):
        erros.append(f"period '{payload.period}' invalido para period_type='anual' (esperado 'YYYY')")
    elif payload.period_type == "trimestral" and not _PERIOD_TRIMESTRAL.match(payload.period):
        erros.append(
            f"period '{payload.period}' invalido para period_type='trimestral' (esperado 'YYYY-Q1'..'YYYY-Q4')"
        )

    for statement in payload.statements:
        if statement.receita_liquida is not None and statement.receita_liquida < 0:
            erros.append(
                f"{statement.statement_type}: receita_liquida nao pode ser negativa ({statement.receita_liquida})"
            )
        if statement.divida_bruta is not None and statement.divida_bruta < 0:
            erros.append(f"{statement.statement_type}: divida_bruta nao pode ser negativa ({statement.divida_bruta})")
        if statement.caixa is not None and statement.caixa < 0:
            erros.append(f"{statement.statement_type}: caixa nao pode ser negativo ({statement.caixa})")

    for indicator in payload.indicators:
        if not indicator.metric_key.strip():
            erros.append("financial indicator com metric_key vazio")

    for operational in payload.operational_data:
        if not operational.metric_key.strip():
            erros.append("operational data com metric_key vazio")

    for debt in payload.debt_maturities:
        if debt.valor is not None and debt.valor <= 0:
            erros.append(f"debt maturity '{debt.descricao}': valor deve ser positivo ({debt.valor})")
        if debt.covenant_status is not None and not (debt.covenant_descricao and debt.covenant_descricao.strip()):
            erros.append(f"debt maturity '{debt.descricao}': covenant_status definido sem covenant_descricao")

    if erros:
        raise IngestValidationError(erros)
