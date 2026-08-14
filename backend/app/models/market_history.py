from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosMarketHistory(Base):
    """Generic market data series (futures curves, macro indicators, ...).

    Maps onto the pre-existing argos_market_history table, extended (via
    migration) with the generic columns below. Legacy columns that may still
    exist on this table are intentionally left unmapped.
    """

    __tablename__ = "argos_market_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    asset: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extra: Mapped[dict | None] = mapped_column("metadata", JSONB(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        # expiration_date is nullable (macro/rate series have none) and Postgres
        # treats every NULL as distinct in a plain multi-column unique index -
        # two macro rows for the same series/date would NOT violate a plain
        # index here, silently duplicating. COALESCE-ing it to a sentinel date
        # makes NULLs compare equal for uniqueness, matching what
        # INSERT ... ON CONFLICT in market_repository.py targets.
        Index(
            "uq_argos_market_history_series",
            "source",
            "category",
            "asset",
            "symbol",
            "metric",
            "reference_date",
            text("COALESCE(expiration_date, DATE '0001-01-01')"),
            unique=True,
        ),
    )
