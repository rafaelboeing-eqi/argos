from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class ArgosMetric(Base):
    """Aggregated indicators computed by Argos (variations, curve vertices, ...).

    Maps onto the pre-existing argos_metrics table, extended (via migration)
    with the generic columns below, mirroring argos_market_history so both
    tables share the same (category, asset, symbol, metric) vocabulary.
    """

    __tablename__ = "argos_metrics"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=False)
    asset: Mapped[str] = mapped_column(String, nullable=False)
    symbol: Mapped[str | None] = mapped_column(String, nullable=True)
    metric: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[float] = mapped_column(Numeric, nullable=False)
    reference_date: Mapped[date] = mapped_column(Date, nullable=False)
    extra: Mapped[dict | None] = mapped_column("metadata", JSONB(none_as_null=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        # symbol is nullable (asset-level metrics like curve vertices/slope
        # have none) - same NULL-distinctness issue as
        # argos_market_history.expiration_date, same COALESCE fix.
        Index(
            "uq_argos_metrics_series",
            "category",
            "asset",
            text("COALESCE(symbol, '')"),
            "metric",
            "reference_date",
            unique=True,
        ),
    )
