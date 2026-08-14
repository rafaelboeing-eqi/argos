from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

# JSONB in production Postgres; plain JSON when tests run against SQLite.
_JSON_TYPE = JSONB().with_variant(JSON(), "sqlite")

from app.models.base import Base


class ArgosMetric(Base):
    """Aggregated indicators computed by Argos (variations, curve vertices, ...).

    Maps onto the pre-existing argos_metrics table, extended (via migration)
    with the generic columns below, mirroring argos_market_history so both
    tables share the same (category, asset, symbol, metric) vocabulary.
    """

    __tablename__ = "argos_metrics"
    __table_args__ = (
        UniqueConstraint(
            "category", "asset", "symbol", "metric", "reference_date",
            name="uq_argos_metrics_series",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    asset: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    extra: Mapped[dict | None] = mapped_column("metadata", _JSON_TYPE, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )
