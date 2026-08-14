"""extend argos_metrics for generic aggregated indicators

Revision ID: e0ed4a2c7c0f
Revises: 19dc5ecf6ad7
Create Date: 2026-08-14 15:48:15.876874

Purely additive, mirrors 19dc5ecf6ad7 for argos_market_history so both
tables share the same (category, asset, symbol, metric) vocabulary.

IMPORTANT - the current real-world schema of argos_metrics was not confirmed
before writing this migration (it predates this change and its original
design assumed a NOT NULL asset_id referencing argos_assets, which this
module deliberately does not depend on yet). Before running
`alembic upgrade head`, check:

    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'argos_metrics'
    ORDER BY ordinal_position;

If a NOT NULL column without a default already exists (e.g. asset_id),
inserts from MarketMetricsService will fail until that constraint is
relaxed - this migration does not touch any pre-existing column.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'e0ed4a2c7c0f'
down_revision: Union[str, None] = '19dc5ecf6ad7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS source TEXT")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS category TEXT")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS asset TEXT")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS symbol TEXT")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS metric TEXT")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS value NUMERIC")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS reference_date DATE")
    op.execute("ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS metadata JSONB")
    op.execute(
        "ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS created_at "
        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )
    op.execute(
        "ALTER TABLE argos_metrics ADD COLUMN IF NOT EXISTS updated_at "
        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_metrics_reference_date ON argos_metrics (reference_date)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_metrics_asset ON argos_metrics (asset)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_metrics_symbol ON argos_metrics (symbol)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_metrics_category ON argos_metrics (category)")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_metrics_series "
        "ON argos_metrics (category, asset, symbol, metric, reference_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_argos_metrics_series")
    op.execute("DROP INDEX IF EXISTS ix_argos_metrics_category")
    op.execute("DROP INDEX IF EXISTS ix_argos_metrics_symbol")
    op.execute("DROP INDEX IF EXISTS ix_argos_metrics_asset")
    op.execute("DROP INDEX IF EXISTS ix_argos_metrics_reference_date")

    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS updated_at")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS metadata")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS reference_date")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS value")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS metric")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS symbol")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS asset")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS category")
    op.execute("ALTER TABLE argos_metrics DROP COLUMN IF EXISTS source")
