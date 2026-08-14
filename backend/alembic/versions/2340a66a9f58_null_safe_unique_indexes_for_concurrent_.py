"""null-safe unique indexes for concurrent upsert

Revision ID: 2340a66a9f58
Revises: 4e6fd070e722
Create Date: 2026-08-14 19:50:55.268995

Postgres treats every NULL as distinct in a plain multi-column unique index,
so the existing uq_argos_market_history_series / uq_argos_metrics_series
indexes never actually stopped two rows with the same
(source, category, asset, symbol, metric, reference_date) from both having
expiration_date = NULL (macro/rate series with no expiration), or, for
argos_metrics, symbol = NULL (asset-level metrics like curve vertices).
That gap is what let a race between two concurrent collector runs insert a
true duplicate instead of hitting the unique index - confirmed empirically
against a real Postgres before writing this migration.

This replaces both indexes with COALESCE-based expression indexes so a NULL
compares equal to itself for uniqueness purposes, which is also the exact
conflict target `INSERT ... ON CONFLICT` now uses in market_repository.py
for atomic, race-free upserts. Index-only change: no data is touched, and
it's reversible (see downgrade).
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '2340a66a9f58'
down_revision: Union[str, None] = '4e6fd070e722'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_argos_market_history_series")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_market_history_series "
        "ON argos_market_history (source, category, asset, symbol, metric, reference_date, "
        "COALESCE(expiration_date, DATE '0001-01-01'))"
    )

    op.execute("DROP INDEX IF EXISTS uq_argos_metrics_series")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_metrics_series "
        "ON argos_metrics (category, asset, COALESCE(symbol, ''), metric, reference_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_argos_market_history_series")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_market_history_series "
        "ON argos_market_history (source, category, asset, symbol, metric, reference_date, expiration_date)"
    )

    op.execute("DROP INDEX IF EXISTS uq_argos_metrics_series")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_metrics_series "
        "ON argos_metrics (category, asset, symbol, metric, reference_date)"
    )
