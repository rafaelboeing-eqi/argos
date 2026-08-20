from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosCollectionRun(Base):
    """Audit trail of the daily market data update job (run_daily_update):
    one row per source per invocation (e.g. "futures_curve:DI1", "macro",
    "treasury:treasury_ipca", "metrics", "rules"), so a single source failing
    is visible without losing the record of every other source that
    succeeded in the same run. `job_run_id` groups every row from one
    invocation together.
    """

    __tablename__ = "argos_collection_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_run_id: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False)  # 'success' | 'error'
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    records_created: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_updated: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_unchanged: Mapped[int | None] = mapped_column(Integer, nullable=True)
    records_skipped: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
