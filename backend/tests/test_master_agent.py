from typing import Any

import pytest
from sqlalchemy.orm import Session

from app.core.database import engine
from app.repositories import credit_repository as repo
from app.services.ai_provider.base import AIProvider, ToolExecutor
from app.services.credit.master_agent import build_master_user_prompt, run_master_analysis


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


VALID_ANALYSIS_OUTPUT = {
    "resumo_executivo": "Empresa estavel, sem deterioracao relevante no periodo.",
    "o_que_mudou": [{"texto": "EBITDA cresceu 5% no periodo (fato).", "tipo": "fato"}],
    "financeiro": [{"texto": "Receita liquida em linha com o esperado.", "tipo": "fato"}],
    "caixa": [{"texto": "Geracao de caixa operacional positiva.", "tipo": "fato"}],
    "endividamento_liquidez": [{"texto": "Divida liquida/EBITDA em 2.0x.", "tipo": "calculo"}],
    "visao_setorial": [{"texto": "Setor Agro em ciclo favoravel (interpretacao setorial).", "tipo": "interpretacao"}],
    "pontos_positivos": [{"texto": "Liquidez corrente confortavel.", "tipo": "fato"}],
    "pontos_atencao": [],
    "red_flags": [],
    "tendencia": "estavel",
    "risco_credito": {"nivel": "baixo", "justificativa": "Indicadores dentro dos limites de covenant."},
    "o_que_monitorar": ["Evolucao da alavancagem no proximo trimestre."],
    "dados_faltantes": [],
    "conclusao": "Capacidade de pagamento preservada.",
}

SECTOR_SPECIALIST_TEXT = "Leitura setorial: setor Agro em ciclo favoravel, sem sinais de deterioracao (interpretacao)."


class ScriptedMasterProvider(AIProvider):
    """Fake dedicado a este teste: distingue a chamada do Master da chamada
    (aninhada, via consult_sector_specialist) do especialista setorial pelo
    formato do output_schema exigido - o unico sinal disponivel na interface
    AIProvider, exatamente como um provider real faria (cada chamada a
    run_agentic_task e independente)."""

    def __init__(self, master_tool_calls: list[tuple[str, dict[str, Any]]]):
        self.master_tool_calls = master_tool_calls
        self.executed_master_tool_calls: list[tuple[str, dict, dict]] = []

    def run_agentic_task(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: ToolExecutor,
        output_schema: dict[str, Any],
        max_turns: int = 20,
    ) -> dict[str, Any]:
        is_sector_specialist_call = output_schema.get("required") == ["texto"]
        if is_sector_specialist_call:
            return {"texto": SECTOR_SPECIALIST_TEXT}

        for name, tool_input in self.master_tool_calls:
            result = tool_executor(name, tool_input)
            self.executed_master_tool_calls.append((name, tool_input, result))
        return VALID_ANALYSIS_OUTPUT


def test_run_master_analysis_delegates_to_sector_specialist_and_validates_output(db):
    company = repo.create_company(db, nome="Master Test Co", setor="Agro")
    db.flush()
    repo.insert_financial_indicator(db, company_id=company.id, period="2025-Q1", metric_key="divida_liquida_ebitda", value=2.0)
    db.flush()

    provider = ScriptedMasterProvider(
        master_tool_calls=[
            ("get_company_profile", {"company_id": company.id}),
            (
                "diff_periods",
                {"company_id": company.id, "metric_key": "divida_liquida_ebitda", "periodo_a": "2025-Q1", "periodo_b": "2025-Q1"},
            ),
            ("consult_sector_specialist", {"setor": "Agro"}),
        ]
    )

    result = run_master_analysis(db, provider, company.id, "Master Test Co", "Agro", period="2025-Q1")

    assert result.output.tendencia == "estavel"
    assert result.output.risco_credito.nivel == "baixo"
    assert result.sector_consultations == [("Agro", SECTOR_SPECIALIST_TEXT)]

    tool_names_called = [name for name, _, _ in provider.executed_master_tool_calls]
    assert tool_names_called == ["get_company_profile", "diff_periods", "consult_sector_specialist"]
    # o resultado da tool consult_sector_specialist ja vem com a leitura setorial embutida
    consult_result = provider.executed_master_tool_calls[2][2]
    assert consult_result == {"setor": "Agro", "leitura_setorial": SECTOR_SPECIALIST_TEXT}


def test_build_master_user_prompt_mentions_period_when_given():
    with_period = build_master_user_prompt("ACME", 1, "Agro", "2025-Q2")
    assert "2025-Q2" in with_period
    without_period = build_master_user_prompt("ACME", 1, "Agro", None)
    assert "periodo mais recente" not in without_period
