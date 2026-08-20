from typing import Any

from app.main import app
from app.services.ai_provider.base import AIProvider, ToolExecutor
from app.services.ai_provider.dependency import get_ai_provider

VALID_ANALYSIS_OUTPUT = {
    "resumo_executivo": "Empresa estavel.",
    "o_que_mudou": [],
    "financeiro": [],
    "caixa": [],
    "endividamento_liquidez": [],
    "visao_setorial": [],
    "pontos_positivos": [],
    "pontos_atencao": [],
    "red_flags": [],
    "tendencia": "estavel",
    "risco_credito": {"nivel": "baixo", "justificativa": "x"},
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
        return VALID_ANALYSIS_OUTPUT


def test_create_and_read_company(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Rota Teste S.A.", "setor": "Agro"})
    assert resp.status_code == 201
    company = resp.json()
    assert company["nome"] == "Rota Teste S.A."

    resp = credit_client.get(f"/api/companies/{company['id']}")
    assert resp.status_code == 200
    assert resp.json()["setor"] == "Agro"

    resp = credit_client.get("/api/companies")
    assert resp.status_code == 200
    assert any(c["id"] == company["id"] for c in resp.json())


def test_read_company_not_found(credit_client):
    resp = credit_client.get("/api/companies/999999")
    assert resp.status_code == 404


def test_trigger_analysis_without_provider_configured_returns_503(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Sem Provider S.A.", "setor": "Agro"})
    company_id = resp.json()["id"]

    resp = credit_client.post(f"/api/companies/{company_id}/analyses", json={})
    assert resp.status_code == 503
    assert "AI Provider" in resp.json()["detail"]


def test_trigger_analysis_with_stub_provider_persists_and_returns_output(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Com Provider S.A.", "setor": "Agro"})
    company_id = resp.json()["id"]

    app.dependency_overrides[get_ai_provider] = lambda: StubProvider()
    try:
        resp = credit_client.post(f"/api/companies/{company_id}/analyses", json={"period": "2025-Q1"})
    finally:
        app.dependency_overrides.pop(get_ai_provider, None)

    assert resp.status_code == 201
    body = resp.json()
    assert body["output"]["risco_credito"]["nivel"] == "baixo"

    resp = credit_client.get(f"/api/companies/{company_id}/analyses")
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    analysis_id = body["analysis_id"]
    resp = credit_client.get(f"/api/companies/{company_id}/analyses/{analysis_id}")
    assert resp.status_code == 200
    assert resp.json()["tendencia"] == "estavel"


def test_ingest_financial_period_without_triggering_analysis(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Ingest S.A.", "setor": "Energia"})
    company_id = resp.json()["id"]

    resp = credit_client.post(
        f"/api/companies/{company_id}/financial-periods",
        json={
            "period": "2025-Q1",
            "period_type": "trimestral",
            "statements": [{"statement_type": "DRE", "ebitda": 1000.0}],
            "dispara_analise": False,
        },
    )
    assert resp.status_code == 201
    assert "nao disparada" in resp.json()["mensagem"]


def test_ingest_financial_period_with_invalid_data_returns_422_and_persists_nothing(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Invalida S.A.", "setor": "Agro"})
    company_id = resp.json()["id"]

    resp = credit_client.post(
        f"/api/companies/{company_id}/financial-periods",
        json={
            "period": "2025-Q1",
            "period_type": "trimestral",
            "statements": [{"statement_type": "BALANCO", "caixa": -50.0}],
            "dispara_analise": False,
        },
    )
    assert resp.status_code == 422
    assert "caixa" in resp.json()["detail"][0]

    resp = credit_client.get(f"/api/companies/{company_id}/financial-statements")
    assert resp.status_code == 200
    assert resp.json() == []


def test_read_financial_data_endpoints_for_unknown_company_return_404(credit_client):
    resp = credit_client.get("/api/companies/999999/financial-statements")
    assert resp.status_code == 404
    resp = credit_client.get("/api/companies/999999/credit-metrics")
    assert resp.status_code == 404
    resp = credit_client.get("/api/companies/999999/financial-indicators")
    assert resp.status_code == 404
    resp = credit_client.get("/api/companies/999999/operational-data")
    assert resp.status_code == 404
    resp = credit_client.get("/api/companies/999999/debt-schedule")
    assert resp.status_code == 404
    resp = credit_client.get("/api/companies/999999/tracked-flags")
    assert resp.status_code == 404


def test_read_financial_data_endpoints_after_ingest(credit_client):
    resp = credit_client.post("/api/companies", json={"nome": "Leitura S.A.", "setor": "Agro"})
    company_id = resp.json()["id"]

    resp = credit_client.post(
        f"/api/companies/{company_id}/financial-periods",
        json={
            "period": "2025-Q1",
            "period_type": "trimestral",
            "statements": [{"statement_type": "DRE", "receita_liquida": 5000.0, "ebitda": 1000.0}],
            "indicators": [{"metric_key": "divida_ebitda", "value": 2.5}],
            "operational_data": [{"metric_key": "area_plantada_ha", "value": 300.0}],
            "debt_maturities": [{"descricao": "Debenture 2027", "vencimento": "2027-06", "valor": 5000.0}],
            "dispara_analise": False,
        },
    )
    assert resp.status_code == 201

    resp = credit_client.get(f"/api/companies/{company_id}/credit-metrics")
    assert resp.status_code == 200
    metrics = resp.json()
    assert metrics[0]["period"] == "2025-Q1"
    assert metrics[0]["margem_ebitda"] == 0.2

    resp = credit_client.get(f"/api/companies/{company_id}/financial-statements")
    assert resp.status_code == 200
    assert resp.json()[0]["ebitda"] == 1000.0

    resp = credit_client.get(f"/api/companies/{company_id}/financial-statements", params={"period": "2024-Q4"})
    assert resp.status_code == 200
    assert resp.json() == []

    resp = credit_client.get(f"/api/companies/{company_id}/financial-indicators")
    assert resp.status_code == 200
    assert resp.json()[0]["metric_key"] == "divida_ebitda"

    resp = credit_client.get(f"/api/companies/{company_id}/operational-data")
    assert resp.status_code == 200
    assert resp.json()[0]["metric_key"] == "area_plantada_ha"

    resp = credit_client.get(f"/api/companies/{company_id}/debt-schedule")
    assert resp.status_code == 200
    assert resp.json()[0]["descricao"] == "Debenture 2027"

    resp = credit_client.get(f"/api/companies/{company_id}/tracked-flags")
    assert resp.status_code == 200
    assert resp.json() == []


def test_sector_knowledge_crud(credit_client):
    resp = credit_client.get("/api/sectors/SetorRotaInexistente/knowledge")
    assert resp.status_code == 404

    payload = {
        "modelo_de_negocio": "x",
        "formacao_receita": "x",
        "estrutura_custos_e_precificacao": "x",
        "margens": "x",
        "capital_de_giro_e_ciclos": "x",
        "oferta_demanda_e_regulacao": "x",
        "capex_e_necessidade_financiamento": "x",
        "riscos_caracteristicos": [],
        "relacoes_causais": [],
        "red_flags": [],
        "contexto_externo": [],
        "monitoramento_continuo": [],
        "indicadores_operacionais_tipicos": [],
    }
    resp = credit_client.put("/api/sectors/SetorRotaNovo/knowledge", json=payload)
    assert resp.status_code == 201
    assert resp.json()["version"] == 1

    resp = credit_client.put("/api/sectors/SetorRotaNovo/knowledge", json=payload)
    assert resp.status_code == 200
    assert resp.json()["version"] == 2

    resp = credit_client.get("/api/sectors/SetorRotaNovo/knowledge")
    assert resp.status_code == 200
    assert resp.json()["version"] == 2


def test_sector_framework_read_empty(credit_client):
    resp = credit_client.get("/api/sectors/SetorSemFramework/framework")
    assert resp.status_code == 200
    body = resp.json()
    assert body["active"] == []
    assert body["proposed"] == []
