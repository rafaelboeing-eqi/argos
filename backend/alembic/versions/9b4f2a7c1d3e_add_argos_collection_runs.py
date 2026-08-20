"""add argos_collection_runs (audit trail for run_daily_update)

Revision ID: 9b4f2a7c1d3e
Revises: 7a1c9e3f5b2d
Create Date: 2026-08-20 00:00:00.000000

Purely additive: one new argos_* table used by the Mercado domain's daily
update job (app/services/market_data/daily_update.py) to record start/end,
status, record counts, and error per source per run. Never touches any
existing table.
"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b4f2a7c1d3e"
down_revision: Union[str, None] = "7a1c9e3f5b2d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "argos_collection_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_run_id", sa.String(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("finished_at", sa.DateTime(), nullable=False),
        sa.Column("records_created", sa.Integer(), nullable=True),
        sa.Column("records_updated", sa.Integer(), nullable=True),
        sa.Column("records_unchanged", sa.Integer(), nullable=True),
        sa.Column("records_skipped", sa.Integer(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_argos_collection_runs_job_run_id", "argos_collection_runs", ["job_run_id"])
    op.create_index("ix_argos_collection_runs_started_at", "argos_collection_runs", ["started_at"])


def downgrade() -> None:
    op.drop_table("argos_collection_runs")
