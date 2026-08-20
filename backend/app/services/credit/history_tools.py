"""Tools de memoria analitica e governanca setorial: framework de metricas
ativo, historico de analises, flag tracker e proposta de novas metricas
(sempre pendente de revisao humana).

Port de tools/historyTools.ts (Argos legado).
"""

from typing import Any

from sqlalchemy.orm import Session

from app.repositories import credit_repository as repo
from app.services.credit.serialization import row_to_dict

GET_SECTOR_FRAMEWORK = {
    "name": "get_sector_framework",
    "description": (
        "Retorna o framework ativo de metricas do especialista setorial: defaults do setor "
        "+ eventuais metricas especificas da empresa."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "setor": {"type": "string"},
            "company_id": {"type": "integer"},
        },
        "required": ["setor"],
    },
}

GET_ANALYSIS_HISTORY = {
    "name": "get_analysis_history",
    "description": (
        "Retorna o historico de analises anteriores de uma empresa (memoria analitica) - "
        "periodo, tendencia, risco de credito e a saida completa de cada rodada."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "company_id": {"type": "integer"},
            "limit": {"type": "integer", "description": "padrao: 8 analises mais recentes"},
        },
        "required": ["company_id"],
    },
}

GET_TRACKED_FLAGS = {
    "name": "get_tracked_flags",
    "description": (
        "Retorna os red flags e pontos de atencao rastreados historicamente para a empresa, "
        "com status (aberto/confirmado/revertido/resolvido)."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"company_id": {"type": "integer"}},
        "required": ["company_id"],
    },
}

PROPOSE_METRIC = {
    "name": "propose_metric",
    "description": (
        "Propoe uma nova metrica para o framework de um setor (ou especifica de uma empresa) "
        "quando voce identificar uma mudanca relevante que as metricas atuais nao capturam. "
        "Fica pendente de revisao humana - nao altera o framework ativo."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "setor": {"type": "string"},
            "company_id": {"type": ["integer", "null"]},
            "metric_key": {"type": "string"},
            "relevancia_credito": {"type": "string"},
            "como_interpretar": {"type": "string"},
            "sinal_melhora": {"type": "string"},
            "sinal_deterioracao": {"type": "string"},
            "fonte_ideal": {"type": "string"},
            "frequencia_atualizacao": {"type": "string"},
            "prioridade": {"type": "string", "enum": ["Essencial", "Relevante", "Complementar"]},
        },
        "required": [
            "setor",
            "metric_key",
            "relevancia_credito",
            "como_interpretar",
            "sinal_melhora",
            "sinal_deterioracao",
            "fonte_ideal",
            "frequencia_atualizacao",
            "prioridade",
        ],
    },
}


def handle_get_sector_framework(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_active_sector_framework(db, input["setor"], company_id=input.get("company_id"))
    return {"framework": [row_to_dict(r) for r in rows]}


def handle_get_analysis_history(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_analysis_history(db, input["company_id"], limit=input.get("limit", 8))
    return {"analyses": [row_to_dict(r) for r in rows]}


def handle_get_tracked_flags(db: Session, input: dict[str, Any]) -> dict:
    rows = repo.get_tracked_flags(db, input["company_id"])
    return {"tracked_flags": [row_to_dict(r) for r in rows]}


def handle_propose_metric(db: Session, input: dict[str, Any]) -> dict:
    row = repo.propose_sector_metric(
        db,
        setor=input["setor"],
        company_id=input.get("company_id"),
        metric_key=input["metric_key"],
        relevancia_credito=input["relevancia_credito"],
        como_interpretar=input["como_interpretar"],
        sinal_melhora=input["sinal_melhora"],
        sinal_deterioracao=input["sinal_deterioracao"],
        fonte_ideal=input["fonte_ideal"],
        frequencia_atualizacao=input["frequencia_atualizacao"],
        prioridade=input["prioridade"],
    )
    return {"proposta": row_to_dict(row)}


HISTORY_TOOLS = [
    (GET_SECTOR_FRAMEWORK, handle_get_sector_framework),
    (GET_ANALYSIS_HISTORY, handle_get_analysis_history),
    (GET_TRACKED_FLAGS, handle_get_tracked_flags),
    (PROPOSE_METRIC, handle_propose_metric),
]
