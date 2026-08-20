"""Tools somente-leitura de dados financeiros/operacionais/divida, expostas ao
Master de Credito e aos especialistas setoriais via tool-use da API da
Anthropic. Quem escreve dados financeiros e a ingestao/ETL (rotas), nunca o
agente - mesma regra do legado.

Port de tools/financialTools.ts (Argos legado). O MCP server do legado
(createSdkMcpServer) nao tem equivalente direto aqui: cada tool e so um par
(definicao JSON Schema, funcao Python) que o loop de tool-use do agente
(services/credit/master_agent.py, sector_agent.py) despacha manualmente.
"""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import credit_repository as repo
from app.services.credit.period_diff import compute_period_diff
from app.services.credit.serialization import row_to_dict

GET_COMPANY_PROFILE = {
    "name": "get_company_profile",
    "description": (
        "Retorna o cadastro da empresa (nome, CNPJ, ticker, setor, grupo economico). "
        "O setor vem daqui, nao e inferido."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"company_id": {"type": "integer"}},
        "required": ["company_id"],
    },
}

GET_FINANCIAL_STATEMENTS = {
    "name": "get_financial_statements",
    "description": (
        "Retorna o historico de DRE/Balanco/Fluxo de Caixa de uma empresa, "
        "opcionalmente filtrado por periodos e tipo de demonstracao."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_id": {"type": "integer"},
            "periods": {
                "type": "array",
                "items": {"type": "string"},
                "description": "ex: ['2024-Q4','2025-Q1']; omitir para todos",
            },
            "statement_type": {"type": "string", "enum": ["DRE", "BALANCO", "FLUXO_CAIXA"]},
        },
        "required": ["company_id"],
    },
}

GET_FINANCIAL_INDICATORS = {
    "name": "get_financial_indicators",
    "description": (
        "Retorna indicadores financeiros (liquidez, alavancagem, cobertura de juros etc.) "
        "de uma empresa ao longo do tempo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_id": {"type": "integer"},
            "periods": {"type": "array", "items": {"type": "string"}},
            "metric_keys": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["company_id"],
    },
}

GET_OPERATIONAL_DATA = {
    "name": "get_operational_data",
    "description": (
        "Retorna metricas operacionais setoriais de uma empresa (ex: area plantada, "
        "capacidade de abate, MW instalado) ao longo do tempo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_id": {"type": "integer"},
            "periods": {"type": "array", "items": {"type": "string"}},
            "metric_keys": {"type": "array", "items": {"type": "string"}},
        },
        "required": ["company_id"],
    },
}

GET_DEBT_SCHEDULE = {
    "name": "get_debt_schedule",
    "description": "Retorna o cronograma de vencimentos de divida e covenants de uma empresa.",
    "input_schema": {
        "type": "object",
        "properties": {"company_id": {"type": "integer"}},
        "required": ["company_id"],
    },
}

DIFF_PERIODS = {
    "name": "diff_periods",
    "description": (
        "Calcula a variacao absoluta e percentual de um indicador financeiro entre dois "
        "periodos (calculo deterministico - use isso em vez de fazer a conta voce mesmo)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_id": {"type": "integer"},
            "metric_key": {
                "type": "string",
                "description": "metric_key em financial_indicators, ou um campo normalizado como 'ebitda', 'divida_liquida' etc.",
            },
            "periodo_a": {"type": "string"},
            "periodo_b": {"type": "string"},
        },
        "required": ["company_id", "metric_key", "periodo_a", "periodo_b"],
    },
}


def handle_get_company_profile(db: Session, input: dict[str, Any]) -> dict:
    company = repo.get_company(db, input["company_id"])
    return row_to_dict(company) if company else {"erro": "empresa nao encontrada"}


def handle_get_financial_statements(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_financial_statements(
        db, input["company_id"], periods=input.get("periods"), statement_type=input.get("statement_type")
    )
    return {"statements": [row_to_dict(r) for r in rows]}


def handle_get_financial_indicators(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_financial_indicators(
        db, input["company_id"], periods=input.get("periods"), metric_keys=input.get("metric_keys")
    )
    return {"indicators": [row_to_dict(r) for r in rows]}


def handle_get_operational_data(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_operational_data(
        db, input["company_id"], periods=input.get("periods"), metric_keys=input.get("metric_keys")
    )
    return {"operational_data": [row_to_dict(r) for r in rows]}


def handle_get_debt_schedule(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_debt_schedule(db, input["company_id"])
    return {"debt_maturities": [row_to_dict(r) for r in rows]}


def handle_diff_periods(db: Session, input: dict[str, Any]) -> dict:
    company_id = input["company_id"]
    metric_key = input["metric_key"]
    periodo_a = input["periodo_a"]
    periodo_b = input["periodo_b"]
    valor_a = repo.get_metric_value_in_period(db, company_id, metric_key, periodo_a)
    valor_b = repo.get_metric_value_in_period(db, company_id, metric_key, periodo_b)
    result = compute_period_diff(metric_key, periodo_a, valor_a, periodo_b, valor_b)
    return result.model_dump()


FINANCIAL_TOOLS = [
    (GET_COMPANY_PROFILE, handle_get_company_profile),
    (GET_FINANCIAL_STATEMENTS, handle_get_financial_statements),
    (GET_FINANCIAL_INDICATORS, handle_get_financial_indicators),
    (GET_OPERATIONAL_DATA, handle_get_operational_data),
    (GET_DEBT_SCHEDULE, handle_get_debt_schedule),
    (DIFF_PERIODS, handle_diff_periods),
]
