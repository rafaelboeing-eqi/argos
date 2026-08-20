"""Toda SQL de acesso ao dominio de credito (empresas, demonstrativos,
indicadores, dados operacionais, divida, framework/conhecimento setorial,
analises e flag tracker) vive aqui. Nada fora deste modulo deve montar uma
query contra essas tabelas - mesma regra de market_repository.py.

Port do acesso a dados hoje espalhado em tools/financialTools.ts,
tools/historyTools.ts, routes/companies.ts, routes/sectors.ts e
services/periodDiff.ts (Argos legado).
"""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, desc, func, or_, select
from sqlalchemy.orm import Session

from app.models.company import ArgosCompany
from app.models.credit_analysis import ArgosCreditAnalysis
from app.models.debt_maturity import ArgosDebtMaturity
from app.models.financial_indicator import ArgosFinancialIndicator
from app.models.financial_statement import ArgosFinancialStatement
from app.models.operational_data import ArgosOperationalDataPoint
from app.models.sector_agent_run import ArgosSectorAgentRun
from app.models.sector_framework import ArgosSectorFrameworkMetric
from app.models.sector_knowledge import ArgosSectorKnowledge
from app.models.tracked_flag import ArgosTrackedFlag

# ---------------------------------------------------------------------------
# Companies
# ---------------------------------------------------------------------------


def create_company(db: Session, **fields: Any) -> ArgosCompany:
    company = ArgosCompany(**fields)
    db.add(company)
    db.flush()
    return company


def list_companies(db: Session) -> list[ArgosCompany]:
    return list(db.execute(select(ArgosCompany).order_by(ArgosCompany.id)).scalars().all())


def get_company(db: Session, company_id: int) -> ArgosCompany | None:
    return db.execute(select(ArgosCompany).where(ArgosCompany.id == company_id)).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Financial statements / indicators / operational data / debt
# ---------------------------------------------------------------------------


def insert_financial_statement(db: Session, **fields: Any) -> ArgosFinancialStatement:
    row = ArgosFinancialStatement(**fields)
    db.add(row)
    return row


def insert_financial_indicator(db: Session, **fields: Any) -> ArgosFinancialIndicator:
    row = ArgosFinancialIndicator(**fields)
    db.add(row)
    return row


def insert_operational_data(db: Session, **fields: Any) -> ArgosOperationalDataPoint:
    row = ArgosOperationalDataPoint(**fields)
    db.add(row)
    return row


def insert_debt_maturity(db: Session, **fields: Any) -> ArgosDebtMaturity:
    row = ArgosDebtMaturity(**fields)
    db.add(row)
    return row


def get_financial_statements(
    db: Session,
    company_id: int,
    periods: list[str] | None = None,
    statement_type: str | None = None,
) -> list[ArgosFinancialStatement]:
    conditions = [ArgosFinancialStatement.company_id == company_id]
    if periods:
        conditions.append(ArgosFinancialStatement.period.in_(periods))
    if statement_type:
        conditions.append(ArgosFinancialStatement.statement_type == statement_type)
    stmt = select(ArgosFinancialStatement).where(and_(*conditions)).order_by(ArgosFinancialStatement.period.asc())
    return list(db.execute(stmt).scalars().all())


def get_financial_indicators(
    db: Session,
    company_id: int,
    periods: list[str] | None = None,
    metric_keys: list[str] | None = None,
) -> list[ArgosFinancialIndicator]:
    conditions = [ArgosFinancialIndicator.company_id == company_id]
    if periods:
        conditions.append(ArgosFinancialIndicator.period.in_(periods))
    if metric_keys:
        conditions.append(ArgosFinancialIndicator.metric_key.in_(metric_keys))
    stmt = select(ArgosFinancialIndicator).where(and_(*conditions)).order_by(ArgosFinancialIndicator.period.asc())
    return list(db.execute(stmt).scalars().all())


def get_operational_data(
    db: Session,
    company_id: int,
    periods: list[str] | None = None,
    metric_keys: list[str] | None = None,
) -> list[ArgosOperationalDataPoint]:
    conditions = [ArgosOperationalDataPoint.company_id == company_id]
    if periods:
        conditions.append(ArgosOperationalDataPoint.period.in_(periods))
    if metric_keys:
        conditions.append(ArgosOperationalDataPoint.metric_key.in_(metric_keys))
    stmt = select(ArgosOperationalDataPoint).where(and_(*conditions)).order_by(ArgosOperationalDataPoint.period.asc())
    return list(db.execute(stmt).scalars().all())


def get_debt_schedule(db: Session, company_id: int) -> list[ArgosDebtMaturity]:
    stmt = (
        select(ArgosDebtMaturity)
        .where(ArgosDebtMaturity.company_id == company_id)
        .order_by(ArgosDebtMaturity.vencimento.asc())
    )
    return list(db.execute(stmt).scalars().all())


_NORMALIZED_STATEMENT_FIELDS = {
    "receita_liquida",
    "ebitda",
    "lucro_liquido",
    "divida_bruta",
    "divida_liquida",
    "caixa",
}


def get_metric_value_in_period(db: Session, company_id: int, metric_key: str, period: str) -> float | None:
    """Valor de uma metrica num periodo, buscando primeiro nos campos
    normalizados de financial_statements e, se nao for um desses campos, no
    EAV de financial_indicators. Usado pelo diff_periods tool.

    Port de services/periodDiff.ts::valorNoPeriodo (Argos legado).
    """
    if metric_key in _NORMALIZED_STATEMENT_FIELDS:
        rows = get_financial_statements(db, company_id, periods=[period])
        for row in rows:
            value = getattr(row, metric_key)
            if value is not None:
                return float(value)
        return None

    stmt = select(ArgosFinancialIndicator).where(
        and_(
            ArgosFinancialIndicator.company_id == company_id,
            ArgosFinancialIndicator.period == period,
            ArgosFinancialIndicator.metric_key == metric_key,
        )
    )
    row = db.execute(stmt).scalar_one_or_none()
    return float(row.value) if row and row.value is not None else None


# ---------------------------------------------------------------------------
# Sector framework (metricas monitoradas, governanca proposed/active/deprecated)
# ---------------------------------------------------------------------------


def get_active_sector_framework(
    db: Session, setor: str, company_id: int | None = None
) -> list[ArgosSectorFrameworkMetric]:
    scope_condition = (
        or_(ArgosSectorFrameworkMetric.company_id.is_(None), ArgosSectorFrameworkMetric.company_id == company_id)
        if company_id is not None
        else ArgosSectorFrameworkMetric.company_id.is_(None)
    )
    stmt = select(ArgosSectorFrameworkMetric).where(
        and_(
            ArgosSectorFrameworkMetric.setor == setor,
            ArgosSectorFrameworkMetric.status == "active",
            scope_condition,
        )
    )
    return list(db.execute(stmt).scalars().all())


def get_proposed_sector_framework(db: Session, setor: str) -> list[ArgosSectorFrameworkMetric]:
    stmt = select(ArgosSectorFrameworkMetric).where(
        and_(ArgosSectorFrameworkMetric.setor == setor, ArgosSectorFrameworkMetric.status == "proposed")
    )
    return list(db.execute(stmt).scalars().all())


def list_active_framework_sectors(db: Session) -> list[str]:
    stmt = (
        select(ArgosSectorFrameworkMetric.setor)
        .where(ArgosSectorFrameworkMetric.status == "active")
        .distinct()
    )
    return [row[0] for row in db.execute(stmt).all()]


def propose_sector_metric(db: Session, **fields: Any) -> ArgosSectorFrameworkMetric:
    row = ArgosSectorFrameworkMetric(**fields, status="proposed")
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# Sector knowledge (conhecimento qualitativo)
# ---------------------------------------------------------------------------


def get_sector_knowledge(db: Session, setor: str) -> ArgosSectorKnowledge | None:
    return db.execute(select(ArgosSectorKnowledge).where(ArgosSectorKnowledge.setor == setor)).scalar_one_or_none()


def list_sector_knowledge(db: Session) -> list[ArgosSectorKnowledge]:
    return list(db.execute(select(ArgosSectorKnowledge)).scalars().all())


def upsert_sector_knowledge(db: Session, setor: str, content: dict) -> ArgosSectorKnowledge:
    existing = get_sector_knowledge(db, setor)
    now = datetime.now(UTC)
    if existing:
        existing.content = content
        existing.version = existing.version + 1
        existing.updated_at = now
        db.flush()
        return existing
    row = ArgosSectorKnowledge(setor=setor, content=content, version=1)
    db.add(row)
    db.flush()
    return row


# ---------------------------------------------------------------------------
# Analyses (memoria analitica)
# ---------------------------------------------------------------------------


def insert_analysis(db: Session, **fields: Any) -> ArgosCreditAnalysis:
    row = ArgosCreditAnalysis(**fields)
    db.add(row)
    db.flush()
    return row


def get_analysis_history(db: Session, company_id: int, limit: int | None = 8) -> list[ArgosCreditAnalysis]:
    stmt = (
        select(ArgosCreditAnalysis)
        .where(ArgosCreditAnalysis.company_id == company_id)
        .order_by(desc(ArgosCreditAnalysis.created_at))
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(db.execute(stmt).scalars().all())


def get_analysis(db: Session, company_id: int, analysis_id: int) -> ArgosCreditAnalysis | None:
    stmt = select(ArgosCreditAnalysis).where(
        and_(ArgosCreditAnalysis.company_id == company_id, ArgosCreditAnalysis.id == analysis_id)
    )
    return db.execute(stmt).scalar_one_or_none()


# ---------------------------------------------------------------------------
# Tracked flags (Flag Tracker)
# ---------------------------------------------------------------------------


def get_tracked_flags(db: Session, company_id: int) -> list[ArgosTrackedFlag]:
    stmt = (
        select(ArgosTrackedFlag)
        .where(ArgosTrackedFlag.company_id == company_id)
        .order_by(desc(ArgosTrackedFlag.updated_at))
    )
    return list(db.execute(stmt).scalars().all())


def insert_tracked_flag(db: Session, **fields: Any) -> ArgosTrackedFlag:
    row = ArgosTrackedFlag(**fields)
    db.add(row)
    return row


def update_tracked_flag_status(db: Session, flag_id: int, status: str, last_seen_analysis_id: int | None = None) -> None:
    flag = db.get(ArgosTrackedFlag, flag_id)
    if flag is None:
        return
    flag.status = status
    flag.updated_at = datetime.now(UTC)
    if last_seen_analysis_id is not None:
        flag.last_seen_analysis_id = last_seen_analysis_id


# ---------------------------------------------------------------------------
# Sector agent runs (auditoria do cruzamento setorial)
# ---------------------------------------------------------------------------


def insert_sector_agent_run(db: Session, **fields: Any) -> ArgosSectorAgentRun:
    row = ArgosSectorAgentRun(**fields)
    db.add(row)
    return row


def get_sector_agent_runs(db: Session, analysis_id: int) -> list[ArgosSectorAgentRun]:
    stmt = select(ArgosSectorAgentRun).where(ArgosSectorAgentRun.analysis_id == analysis_id)
    return list(db.execute(stmt).scalars().all())
