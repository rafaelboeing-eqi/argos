from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.repositories import credit_repository as repo
from app.schemas.company import Company, CompanyCreate, IngestPeriodRequest
from app.services.ai_provider.base import AIProvider
from app.services.ai_provider.dependency import get_ai_provider, require_ai_provider
from app.services.credit.analysis_runner import analyze_company

router = APIRouter(prefix="/api/companies", tags=["credit"])


def _to_company(row) -> Company:
    return Company(
        id=row.id,
        nome=row.nome,
        cnpj=row.cnpj,
        ticker=row.ticker,
        setor=row.setor,
        grupo_economico=row.grupo_economico,
        created_at=row.created_at,
    )


@router.get("", response_model=list[Company])
def list_companies(db: Session = Depends(get_db)) -> list[Company]:
    return [_to_company(row) for row in repo.list_companies(db)]


@router.post("", response_model=Company, status_code=201)
def create_company(payload: CompanyCreate, db: Session = Depends(get_db)) -> Company:
    row = repo.create_company(db, **payload.model_dump())
    db.commit()
    return _to_company(row)


@router.get("/{company_id}", response_model=Company)
def read_company(company_id: int, db: Session = Depends(get_db)) -> Company:
    row = repo.get_company(db, company_id)
    if row is None:
        raise HTTPException(status_code=404, detail="empresa nao encontrada")
    return _to_company(row)


@router.post("/{company_id}/financial-periods", status_code=201)
def ingest_financial_period(
    company_id: int,
    payload: IngestPeriodRequest,
    db: Session = Depends(get_db),
    provider: AIProvider | None = Depends(get_ai_provider),
) -> dict:
    """Ingestao manual/mock de um novo periodo - o cenario-alvo desta fase, ja
    que ainda nao ha integracao com uma fonte real (CVM, sistema interno etc.).
    Dispara a analise automaticamente ao final, a menos que
    dispara_analise=false."""
    company = repo.get_company(db, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="empresa nao encontrada")

    for statement in payload.statements:
        repo.insert_financial_statement(
            db, company_id=company_id, period=payload.period, period_type=payload.period_type, **statement.model_dump()
        )
    for indicator in payload.indicators:
        repo.insert_financial_indicator(db, company_id=company_id, period=payload.period, **indicator.model_dump())
    for operational in payload.operational_data:
        repo.insert_operational_data(db, company_id=company_id, period=payload.period, **operational.model_dump())
    for debt in payload.debt_maturities:
        repo.insert_debt_maturity(db, company_id=company_id, **debt.model_dump())
    db.commit()

    if not payload.dispara_analise:
        return {"mensagem": "dados ingeridos, analise nao disparada (dispara_analise=false)"}

    resolved_provider = require_ai_provider(provider)
    try:
        result = analyze_company(db, resolved_provider, company_id, payload.period)
    except Exception as err:
        raise HTTPException(status_code=502, detail=f"dados ingeridos, mas a analise falhou: {err}") from err
    return {"analysis_id": result.analysis_id, "output": result.output.model_dump()}
