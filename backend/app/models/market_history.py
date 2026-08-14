from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# JSONB in production Postgres; plain JSON when tests run against SQLite.
_JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")

from app.models.base import Base


class ArgosMarketHistory(Base):
    """Generic market data series (futures curves, macro indicators, ...).

    Maps onto the pre-existing argos_market_history table, extended (via
    migration) with the generic columns below. Legacy columns that may still
    exist on this table are intentionally left unmapped.
    """

    __tablename__ = "argos_market_history"
    __table_args__ = (
        UniqueConstraint(
            "source", "category", "asset", "symbol", "metric", "reference_date", "expiration_date",
            name="uq_argos_market_history_series",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    asset: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str] = mapped_column(String, nullable=False)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    extra: Mapped[dict | None] = mapped_column("metadata", _JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
