from app.models.financial_statement import ArgosFinancialStatement
from app.services.credit.metrics import compute_credit_metrics, compute_credit_metrics_series


def _statement(**fields) -> ArgosFinancialStatement:
    return ArgosFinancialStatement(company_id=1, period="2025-Q1", period_type="trimestral", **fields)


def test_compute_credit_metrics_merges_dre_and_balanco_rows_and_computes_ratios():
    dre = _statement(statement_type="DRE", receita_liquida=1000.0, ebitda=200.0, lucro_liquido=50.0)
    balanco = _statement(statement_type="BALANCO", divida_bruta=800.0, divida_liquida=600.0, caixa=200.0)

    metrics = compute_credit_metrics("2025-Q1", [dre, balanco])

    assert metrics.margem_ebitda == 0.2
    assert metrics.margem_liquida == 0.05
    assert metrics.divida_liquida_ebitda == 3.0
    assert metrics.divida_bruta_ebitda == 4.0
    assert metrics.caixa_sobre_divida_bruta == 0.25


def test_compute_credit_metrics_returns_none_ratios_when_denominator_missing_or_zero():
    row = _statement(statement_type="DRE", receita_liquida=0.0, ebitda=None, lucro_liquido=10.0)

    metrics = compute_credit_metrics("2025-Q1", [row])

    assert metrics.margem_ebitda is None
    assert metrics.margem_liquida is None
    assert metrics.divida_liquida_ebitda is None
    assert metrics.divida_bruta_ebitda is None
    assert metrics.caixa_sobre_divida_bruta is None


def test_compute_credit_metrics_series_groups_by_period_preserving_order():
    q1_dre = ArgosFinancialStatement(
        company_id=1, period="2025-Q1", period_type="trimestral", statement_type="DRE",
        receita_liquida=1000.0, ebitda=200.0,
    )
    q2_dre = ArgosFinancialStatement(
        company_id=1, period="2025-Q2", period_type="trimestral", statement_type="DRE",
        receita_liquida=1100.0, ebitda=220.0,
    )
    q1_balanco = ArgosFinancialStatement(
        company_id=1, period="2025-Q1", period_type="trimestral", statement_type="BALANCO",
        divida_bruta=800.0,
    )

    series = compute_credit_metrics_series([q1_dre, q2_dre, q1_balanco])

    assert [m.period for m in series] == ["2025-Q1", "2025-Q2"]
    assert series[0].divida_bruta == 800.0
    assert series[0].margem_ebitda == 0.2
    assert series[1].margem_ebitda == 0.2
