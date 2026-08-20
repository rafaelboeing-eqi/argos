"""Comparacao deterministica entre dois periodos de uma metrica de credito.

Port de services/periodDiff.ts (Argos legado). Calculo mantido em codigo, NUNCA
delegado ao LLM, para nunca correr risco de erro aritmetico numa comparacao
entre periodos - o Master/especialista setorial devem sempre chamar a tool
correspondente em vez de calcular variacao "de cabeca".
"""

from pydantic import BaseModel


class PeriodDiffResult(BaseModel):
    metric_key: str
    periodo_a: str
    valor_a: float | None
    periodo_b: str
    valor_b: float | None
    delta_absoluto: float | None
    delta_percentual: float | None
    erro: str | None = None


def compute_period_diff(
    metric_key: str,
    periodo_a: str,
    valor_a: float | None,
    periodo_b: str,
    valor_b: float | None,
) -> PeriodDiffResult:
    if valor_a is None or valor_b is None:
        return PeriodDiffResult(
            metric_key=metric_key,
            periodo_a=periodo_a,
            valor_a=valor_a,
            periodo_b=periodo_b,
            valor_b=valor_b,
            delta_absoluto=None,
            delta_percentual=None,
            erro="valor ausente em um dos periodos",
        )

    delta_absoluto = valor_b - valor_a
    # Denominador usa abs(valor_a) (nao valor_a puro) para que o sinal do delta
    # percentual sempre reflita a direcao real da variacao mesmo quando a base
    # e negativa (ex: lucro liquido saindo de prejuizo) - mesma semantica do
    # legado, deliberadamente distinta de normalizers.compute_pct_change (que
    # serve dados de mercado, sempre positivos).
    delta_percentual = (delta_absoluto / abs(valor_a)) * 100 if valor_a != 0 else None

    return PeriodDiffResult(
        metric_key=metric_key,
        periodo_a=periodo_a,
        valor_a=valor_a,
        periodo_b=periodo_b,
        valor_b=valor_b,
        delta_absoluto=delta_absoluto,
        delta_percentual=delta_percentual,
    )
