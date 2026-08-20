from typing import Any

import pytest

from app.repositories import credit_repository as repo
from app.services.ai_provider.base import AIProvider, ToolExecutor
from app.services.credit.analysis_runner import analyze_company

VALID_ANALYSIS_OUTPUT = {
    "resumo_executivo": "Empresa estavel.",
    "o_que_mudou": [],
    "financeiro": [],
    "caixa": [],
    "endividamento_liquidez": [],
    "visao_setorial": [],
    "pontos_positivos": [],
    "pontos_atencao": [],
    "red_flags": [{"texto": "Concentracao de receita em poucos clientes", "tipo": "fato"}],
    "tendencia": "estavel",
    "risco_credito": {"nivel": "moderado", "justificativa": "x"},
    "o_que_monitorar": [],
    "dados_faltantes": [],
    "conclusao": "x",
}


class StubProvider(AIProvider):
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
        if output_schema.get("required") == ["texto"]:
            return {"texto": "leitura setorial (stub)"}
        tool_executor("get_company_profile", {"company_id": 1})
        return VALID_ANALYSIS_OUTPUT


def test_analyze_company_persists_analysis_sector_run_and_tracked_flag(real_db_committable):
    db = real_db_committable
    company = repo.create_company(db, nome="Runner Co", setor="Agro")
    db.commit()

    result = analyze_company(db, StubProvider(), company.id, period="2025-Q1")

    assert result.output.risco_credito.nivel == "moderado"

    persisted = repo.get_analysis(db, company.id, result.analysis_id)
    assert persisted is not None
    assert persisted.tendencia == "estavel"
    assert persisted.output["conclusao"] == "x"

    sector_runs = repo.get_sector_agent_runs(db, result.analysis_id)
    assert len(sector_runs) == 0  # StubProvider nao chama consult_sector_specialist

    flags = repo.get_tracked_flags(db, company.id)
    assert len(flags) == 1
    assert flags[0].status == "aberto"
    assert flags[0].descricao == "Concentracao de receita em poucos clientes"


def test_analyze_company_raises_for_unknown_company(real_db_committable):
    with pytest.raises(ValueError, match="nao encontrada"):
        analyze_company(real_db_committable, StubProvider(), 999999)
