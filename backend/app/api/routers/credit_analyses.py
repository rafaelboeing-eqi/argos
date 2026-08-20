from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import credit_repository as repo
from app.schemas.company import TriggerAnalysisRequest
from app.services.ai_provider.base import AIProvider
from app.services.ai_provider.dependency import get_ai_provider, require_ai_provider
from app.services.credit.analysis_runner import analyze_company

# Montado em /api/companies/{company_id}/analyses (ver app/main.py).
router = APIRouter(prefix="/api/companies/{company_id}/analyses", tags=["credit"])


def _analysis_to_dict(row) -> dict:
    return {
        "id": row.id,
        "company_id": row.company_id,
        "period": row.period,
        "output": row.output,
        "tendencia": row.tendencia,
        "risco_credito": row.risco_credito,
        "created_at": row.created_at,
    }


@router.post("", status_code=201)
def trigger_analysis(
    company_id: int,
    payload: TriggerAnalysisRequest,
    db: Session = Depends(get_db),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> dict:
    """Disparo manual de uma analise (sem ingestao de novos dados) - usa o
    historico ja existente no banco para a empresa."""
    resolved_provider = require_ai_provider(provider)
    try:
        result = analyze_company(db, resolved_provider, company_id, payload.period)
    except ValueError as err:
        raise HTTPException(status_code=404, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"falha ao rodar a analise: {err}") from err
    return {"analysis_id": result.analysis_id, "output": result.output.model_dump()}


@router.get("")
def list_analyses(company_id: int, db: Session = Depends(get_db)) -> list[dict]:
    """Memoria analitica da empresa: todas as analises ja feitas."""
    rows = repo.get_analysis_history(db, company_id, limit=None)
    return [_analysis_to_dict(row) for row in rows]


@router.get("/{analysis_id}")
def read_analysis(company_id: int, analysis_id: int, db: Session = Depends(get_db)) -> dict:
    row = repo.get_analysis(db, company_id, analysis_id)
    if row is None:
        raise HTTPException(status_code=404, detail="analise nao encontrada")
    sector_runs = repo.get_sector_agent_runs(db, analysis_id)
    return {
        **_analysis_to_dict(row),
        "sector_agent_runs": [
            {"id": s.id, "setor": s.setor, "raw_output": s.raw_output, "created_at": s.created_at} for s in sector_runs
        ],
    }
