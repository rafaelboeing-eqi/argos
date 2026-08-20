import pytest

from app.schemas.company import DebtMaturityInput, FinancialIndicatorInput, FinancialStatementInput, IngestPeriodRequest
from app.services.credit.ingestion_validation import IngestValidationError, validate_ingest_period


def _payload(**overrides) -> IngestPeriodRequest:
    fields = {"period": "2025-Q1", "period_type": "trimestral"}
    fields.update(overrides)
    return IngestPeriodRequest(**fields)


def test_valid_payload_raises_nothing():
    validate_ingest_period(_payload(statements=[FinancialStatementInput(statement_type="DRE", receita_liquida=100.0)]))


@pytest.mark.parametrize(
    "period,period_type",
    [("2025", "trimestral"), ("2025-Q5", "trimestral"), ("2025-Q1", "anual"), ("Q1-2025", "anual")],
)
def test_period_format_must_match_period_type(period, period_type):
    with pytest.raises(IngestValidationError):
        validate_ingest_period(_payload(period=period, period_type=period_type))


def test_negative_receita_liquida_is_rejected():
    payload = _payload(statements=[FinancialStatementInput(statement_type="DRE", receita_liquida=-10.0)])
    with pytest.raises(IngestValidationError) as exc_info:
        validate_ingest_period(payload)
    assert "receita_liquida" in exc_info.value.erros[0]


def test_negative_lucro_liquido_is_allowed_prejuizo_is_valid():
    payload = _payload(statements=[FinancialStatementInput(statement_type="DRE", lucro_liquido=-500.0)])
    validate_ingest_period(payload)


def test_negative_divida_bruta_or_caixa_is_rejected():
    with pytest.raises(IngestValidationError):
        validate_ingest_period(_payload(statements=[FinancialStatementInput(statement_type="BALANCO", divida_bruta=-1.0)]))
    with pytest.raises(IngestValidationError):
        validate_ingest_period(_payload(statements=[FinancialStatementInput(statement_type="BALANCO", caixa=-1.0)]))


def test_blank_metric_key_is_rejected():
    with pytest.raises(IngestValidationError):
        validate_ingest_period(_payload(indicators=[FinancialIndicatorInput(metric_key="   ", value=1.0)]))


def test_non_positive_debt_maturity_valor_is_rejected():
    with pytest.raises(IngestValidationError):
        validate_ingest_period(_payload(debt_maturities=[DebtMaturityInput(descricao="Debenture", valor=0.0)]))


def test_covenant_status_without_covenant_descricao_is_rejected():
    with pytest.raises(IngestValidationError):
        validate_ingest_period(
            _payload(debt_maturities=[DebtMaturityInput(descricao="Debenture", covenant_status="violado")])
        )


def test_covenant_status_with_covenant_descricao_is_accepted():
    validate_ingest_period(
        _payload(
            debt_maturities=[
                DebtMaturityInput(
                    descricao="Debenture", covenant_status="violado", covenant_descricao="Divida/EBITDA > 3.5x"
                )
            ]
        )
    )
