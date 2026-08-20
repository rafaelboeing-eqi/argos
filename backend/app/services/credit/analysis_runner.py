"""Ponto unico de orquestracao do dominio de credito: roda o Master, persiste
a analise, audita as consultas ao(s) especialista(s) setorial(is) e
reconcilia a memoria de red flags/pontos de atencao (Flag Tracker). Usado
tanto pelo disparo manual (POST /analyses) quanto pelo disparo automatico
apos ingestao de um novo periodo (POST /financial-periods).

Port de services/analysisRunner.ts (Argos legado).
"""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.repositories import credit_repository as repo
from app.schemas.credit_analysis import AnalysisOutput
from app.services.ai_provider.base import AIProvider
from app.services.credit.flag_tracker import reconcile_tracked_flags
from app.services.credit.master_agent import run_master_analysis


@dataclass
class AnalyzeCompanyResult:
    analysis_id: int
    output: AnalysisOutput


def analyze_company(
    db: Session, provider: AIProvider, company_id: int, period: str | None = None
) -> AnalyzeCompanyResult:
    company = repo.get_company(db, company_id)
    if company is None:
        raise ValueError(f"empresa {company_id} nao encontrada")

    master_result = run_master_analysis(db, provider, company.id, company.nome, company.setor, period)
    output = master_result.output

    analysis = repo.insert_analysis(
        db,
        company_id=company.id,
        period=period or "mais-recente",
        output=output.model_dump(mode="json"),
        tendencia=output.tendencia,
        risco_credito=output.risco_credito.nivel,
    )
    db.flush()

    for setor, texto in master_result.sector_consultations:
        repo.insert_sector_agent_run(db, analysis_id=analysis.id, setor=setor, raw_output={"texto": texto})

    reconcile_tracked_flags(db, company.id, analysis.id, output)

    # Unidade de trabalho atomica: analise + auditoria setorial + flag tracker
    # sao persistidos juntos, ou nada e persistido - mesmo espirito do
    # commit unico ao final de MarketMetricsService.compute_all.
    db.commit()

    return AnalyzeCompanyResult(analysis_id=analysis.id, output=output)
