"""Testes das tools de credito (financial_tools, history_tools, tool_registry)
contra o Postgres real, sempre em transacao com rollback - mesmo padrao de
tests/test_credit_repository.py."""

import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories import credit_repository as repo
from app.services.credit import tool_registry
from app.services.credit.financial_tools import handle_diff_periods, handle_get_company_profile
from app.services.credit.history_tools import handle_get_tracked_flags, handle_propose_metric


@pytest.fixture()
def db():
    if engine is None:
        pytest.skip("Postgres real nao configurado neste ambiente")
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


def test_registry_exposes_all_ten_tools():
    assert len(tool_registry.ALL_TOOL_NAMES) == 10
    defs = tool_registry.get_tool_definitions(["get_company_profile", "diff_periods"])
    assert [d["name"] for d in defs] == ["get_company_profile", "diff_periods"]


def test_get_company_profile_tool_found_and_not_found(db):
    company = repo.create_company(db, nome="Tools Teste", setor="Agro")
    db.flush()

    found = handle_get_company_profile(db, {"company_id": company.id})
    assert found["nome"] == "Tools Teste"

    not_found = handle_get_company_profile(db, {"company_id": 999999})
    assert not_found == {"erro": "empresa nao encontrada"}


def test_diff_periods_tool_via_dispatcher(db):
    company = repo.create_company(db, nome="DiffTools", setor="Energia")
    db.flush()
    repo.insert_financial_indicator(db, company_id=company.id, period="2025-Q1", metric_key="divida_liquida_ebitda", value=3.0)
    repo.insert_financial_indicator(db, company_id=company.id, period="2025-Q2", metric_key="divida_liquida_ebitda", value=2.5)
    db.flush()

    result = tool_registry.execute_tool(
        db,
        "diff_periods",
        {"company_id": company.id, "metric_key": "divida_liquida_ebitda", "periodo_a": "2025-Q1", "periodo_b": "2025-Q2"},
    )
    assert result["valor_a"] == 3.0
    assert result["valor_b"] == 2.5
    assert result["delta_absoluto"] == -0.5
    assert result["erro"] is None


def test_diff_periods_tool_missing_period_reports_erro(db):
    company = repo.create_company(db, nome="DiffMissing", setor="Agro")
    db.flush()
    result = handle_diff_periods(
        db, {"company_id": company.id, "metric_key": "ebitda", "periodo_a": "2025-Q1", "periodo_b": "2025-Q2"}
    )
    assert result["erro"] == "valor ausente em um dos periodos"


def test_propose_metric_and_get_tracked_flags_tools(db):
    result = handle_propose_metric(
        db,
        {
            "setor": "Saneamento",
            "metric_key": "perdas_agua_pct",
            "relevancia_credito": "x",
            "como_interpretar": "x",
            "sinal_melhora": "x",
            "sinal_deterioracao": "x",
            "fonte_ideal": "x",
            "frequencia_atualizacao": "Trimestral",
            "prioridade": "Relevante",
        },
    )
    assert result["proposta"]["status"] == "proposed"

    company = repo.create_company(db, nome="FlagsTools", setor="Agro")
    db.flush()
    flags = handle_get_tracked_flags(db, {"company_id": company.id})
    assert flags == {"tracked_flags": []}


def test_unknown_tool_returns_erro(db):
    result = tool_registry.execute_tool(db, "tool_que_nao_existe", {})
    assert "erro" in result
