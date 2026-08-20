"""Motor de calculo de indicadores de credito a partir dos demonstrativos
financeiros normalizados (argos_financial_statements). Calculo mantido em
codigo, nunca delegado ao LLM - mesma razao de period_diff.py.

Um mesmo periodo pode ter varias linhas em financial_statements (uma por
statement_type: DRE, BALANCO, FLUXO_CAIXA), cada uma com um subconjunto dos
campos normalizados preenchido. `merge_period_fields` funde essas linhas num
unico conjunto de valores antes de calcular os indicadores.
"""

from pydantic import BaseModel

from app.models.financial_statement import ArgosFinancialStatement

_NORMALIZED_FIELDS = (
    "receita_liquida",
    "ebitda",
    "lucro_liquido",
    "divida_bruta",
    "divida_liquida",
    "caixa",
)


class CreditMetrics(BaseModel):
    period: str
    receita_liquida: float | None = None
    ebitda: float | None = None
    lucro_liquido: float | None = None
    divida_bruta: float | None = None
    divida_liquida: float | None = None
    caixa: float | None = None
    margem_ebitda: float | None = None
    margem_liquida: float | None = None
    divida_liquida_ebitda: float | None = None
    divida_bruta_ebitda: float | None = None
    caixa_sobre_divida_bruta: float | None = None


def _safe_ratio(numerador: float | None, denominador: float | None) -> float | None:
    if numerador is None or denominador is None or denominador == 0:
        return None
    return numerador / denominador


def merge_period_fields(statements: list[ArgosFinancialStatement]) -> dict[str, float | None]:
    """Funde os campos normalizados das linhas (DRE/BALANCO/FLUXO_CAIXA) de um
    mesmo periodo, preferindo o primeiro valor nao-nulo encontrado para cada
    campo."""
    merged: dict[str, float | None] = {field: None for field in _NORMALIZED_FIELDS}
    for row in statements:
        for field in _NORMALIZED_FIELDS:
            if merged[field] is None:
                value = getattr(row, field)
                if value is not None:
                    merged[field] = float(value)
    return merged


def compute_credit_metrics(period: str, statements: list[ArgosFinancialStatement]) -> CreditMetrics:
    fields = merge_period_fields(statements)
    return CreditMetrics(
        period=period,
        **fields,
        margem_ebitda=_safe_ratio(fields["ebitda"], fields["receita_liquida"]),
        margem_liquida=_safe_ratio(fields["lucro_liquido"], fields["receita_liquida"]),
        divida_liquida_ebitda=_safe_ratio(fields["divida_liquida"], fields["ebitda"]),
        divida_bruta_ebitda=_safe_ratio(fields["divida_bruta"], fields["ebitda"]),
        caixa_sobre_divida_bruta=_safe_ratio(fields["caixa"], fields["divida_bruta"]),
    )


def compute_credit_metrics_series(statements: list[ArgosFinancialStatement]) -> list[CreditMetrics]:
    """Agrupa demonstrativos (de varios statement_type e periodos, ja
    ordenados por periodo) por periodo e calcula os indicadores de cada um,
    preservando a ordem de primeira ocorrencia dos periodos."""
    by_period: dict[str, list[ArgosFinancialStatement]] = {}
    for row in statements:
        by_period.setdefault(row.period, []).append(row)
    return [compute_credit_metrics(period, rows) for period, rows in by_period.items()]
