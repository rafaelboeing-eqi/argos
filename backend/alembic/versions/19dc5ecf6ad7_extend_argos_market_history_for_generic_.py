"""extend argos_market_history for generic market series

Revision ID: 19dc5ecf6ad7
Revises:
Create Date: 2026-08-14 15:48:15.508115

Purely additive: only adds nullable columns and indexes to the existing
argos_market_history table. Never drops or renames anything, so any legacy
columns already on this table are left untouched.

IMPORTANT - verify before running `alembic upgrade head` against the real
database: if argos_market_history already has a NOT NULL column without a
default (e.g. a legacy asset_id foreign key), inserts from the new generic
collector will fail until that constraint is relaxed. Run this first and
review the output:

    SELECT column_name, data_type, is_nullable, column_default
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'argos_market_history'
    ORDER BY ordinal_position;
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '19dc5ecf6ad7'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS source TEXT")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS category TEXT")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS asset TEXT")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS symbol TEXT")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS metric TEXT")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS value NUMERIC")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS reference_date DATE")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS expiration_date DATE")
    op.execute("ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS metadata JSONB")
    op.execute(
        "ALTER TABLE argos_market_history ADD COLUMN IF NOT EXISTS created_at "
        "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_argos_market_history_reference_date "
        "ON argos_market_history (reference_date)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_market_history_asset ON argos_market_history (asset)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_argos_market_history_symbol ON argos_market_history (symbol)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_argos_market_history_category ON argos_market_history (category)"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_argos_market_history_series "
        "ON argos_market_history (source, category, asset, symbol, metric, reference_date, expiration_date)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_argos_market_history_series")
    op.execute("DROP INDEX IF EXISTS ix_argos_market_history_category")
    op.execute("DROP INDEX IF EXISTS ix_argos_market_history_symbol")
    op.execute("DROP INDEX IF EXISTS ix_argos_market_history_asset")
    op.execute("DROP INDEX IF EXISTS ix_argos_market_history_reference_date")

    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS created_at")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS metadata")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS expiration_date")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS reference_date")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS value")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS metric")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS symbol")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS asset")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS category")
    op.execute("ALTER TABLE argos_market_history DROP COLUMN IF EXISTS source")
