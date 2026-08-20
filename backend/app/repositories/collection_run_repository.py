"""All SQL access to argos_collection_runs lives here - the audit trail of
run_daily_update(). Nothing outside this module should build a query against
this table.
"""

from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.models.collection_run import ArgosCollectionRun


def insert_collection_run(db: Session, **fields: Any) -> ArgosCollectionRun:
    row = ArgosCollectionRun(**fields)
    db.add(row)
    db.flush()
    return row


def list_recent_runs(db: Session, limit: int = 50) -> list[ArgosCollectionRun]:
    stmt = select(ArgosCollectionRun).order_by(desc(ArgosCollectionRun.started_at)).limit(limit)
    return list(db.execute(stmt).scalars().all())


def list_runs_for_job(db: Session, job_run_id: str) -> list[ArgosCollectionRun]:
    stmt = (
        select(ArgosCollectionRun)
        .where(ArgosCollectionRun.job_run_id == job_run_id)
        .order_by(ArgosCollectionRun.started_at.asc())
    )
    return list(db.execute(stmt).scalars().all())
