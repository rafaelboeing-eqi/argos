from app.services.credit.period_diff import compute_period_diff


def test_compute_period_diff_basic_growth():
    result = compute_period_diff("ebitda", "2024-Q4", 100.0, "2025-Q1", 110.0)
    assert result.delta_absoluto == 10.0
    assert result.delta_percentual == 10.0
    assert result.erro is None


def test_compute_period_diff_missing_value_reports_erro():
    result = compute_period_diff("ebitda", "2024-Q4", None, "2025-Q1", 110.0)
    assert result.delta_absoluto is None
    assert result.delta_percentual is None
    assert result.erro == "valor ausente em um dos periodos"


def test_compute_period_diff_zero_base_has_no_percentual():
    result = compute_period_diff("lucro_liquido", "2024-Q4", 0.0, "2025-Q1", 50.0)
    assert result.delta_absoluto == 50.0
    assert result.delta_percentual is None


def test_compute_period_diff_negative_base_uses_absolute_denominator():
    # Empresa saiu de prejuizo (-100) para lucro (50): delta absoluto = 150,
    # e o percentual deve refletir melhora (positivo), nao inverter o sinal
    # por causa de uma base negativa no denominador.
    result = compute_period_diff("lucro_liquido", "2024-Q4", -100.0, "2025-Q1", 50.0)
    assert result.delta_absoluto == 150.0
    assert result.delta_percentual == 150.0
