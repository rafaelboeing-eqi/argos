"""add credit domain tables (argos_companies, argos_financial_statements,
argos_financial_indicators, argos_debt_maturities, argos_operational_data,
argos_sector_knowledge, argos_sector_frameworks, argos_analyses,
argos_tracked_flags, argos_sector_agent_runs)

Revision ID: 7a1c9e3f5b2d
Revises: 2340a66a9f58
Create Date: 2026-08-19 18:00:00.000000

Purely additive: creates 10 new argos_* tables for the credit domain (Master
de Credito, especialistas setoriais, Flag Tracker). Never touches any
existing table.

IMPORTANT: written by hand instead of `alembic revision --autogenerate` -
autogenerate diffs against every table actually present in the `public`
schema of `features`, not just the ones mapped on Base.metadata, so it also
proposed dropping dozens of unrelated corporate tables (aderencia_*,
follow_*, martini_*, ntnb_*, and even the pre-existing argos_assets/
argos_events/argos_event_history, none of which are modeled here). That
generated file was discarded without ever running `alembic upgrade` against
it. Keep writing credit-domain migrations by hand (or heavily hand-edit any
future autogenerate output) until every pre-existing argos_* table has a
matching SQLAlchemy model - see alembic/env.py's own warning about this.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7a1c9e3f5b2d"
down_revision: Union[str, None] = "2340a66a9f58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "argos_companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("nome", sa.String(), nullable=False),
        sa.Column("cnpj", sa.String(), nullable=True),
        sa.Column("ticker", sa.String(), nullable=True),
        sa.Column("setor", sa.String(), nullable=False),
        sa.Column("grupo_economico", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "argos_financial_statements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("period_type", sa.String(), nullable=False),
        sa.Column("statement_type", sa.String(), nullable=False),
        sa.Column("receita_liquida", sa.Numeric(), nullable=True),
        sa.Column("ebitda", sa.Numeric(), nullable=True),
        sa.Column("lucro_liquido", sa.Numeric(), nullable=True),
        sa.Column("divida_bruta", sa.Numeric(), nullable=True),
        sa.Column("divida_liquida", sa.Numeric(), nullable=True),
        sa.Column("caixa", sa.Numeric(), nullable=True),
        sa.Column("raw_json", postgresql.JSONB(none_as_null=True), nullable=True),
        sa.Column("fonte", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_argos_financial_statements_company_period",
        "argos_financial_statements",
        ["company_id", "period"],
    )

    op.create_table(
        "argos_financial_indicators",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("metric_key", sa.String(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("fonte", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_argos_financial_indicators_company_period_metric",
        "argos_financial_indicators",
        ["company_id", "period", "metric_key"],
    )

    op.create_table(
        "argos_operational_data",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("metric_key", sa.String(), nullable=False),
        sa.Column("value", sa.Numeric(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("fonte", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_argos_operational_data_company_period_metric",
        "argos_operational_data",
        ["company_id", "period", "metric_key"],
    )

    op.create_table(
        "argos_debt_maturities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("descricao", sa.String(), nullable=False),
        sa.Column("vencimento", sa.String(), nullable=True),
        sa.Column("valor", sa.Numeric(), nullable=True),
        sa.Column("covenant_descricao", sa.String(), nullable=True),
        sa.Column("covenant_status", sa.String(), nullable=True),
        sa.Column("fonte", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "argos_sector_knowledge",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setor", sa.String(), nullable=False, unique=True),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )

    op.create_table(
        "argos_sector_frameworks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("setor", sa.String(), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=True),
        sa.Column("metric_key", sa.String(), nullable=False),
        sa.Column("relevancia_credito", sa.Text(), nullable=False),
        sa.Column("como_interpretar", sa.Text(), nullable=False),
        sa.Column("sinal_melhora", sa.Text(), nullable=False),
        sa.Column("sinal_deterioracao", sa.Text(), nullable=False),
        sa.Column("fonte_ideal", sa.String(), nullable=False),
        sa.Column("frequencia_atualizacao", sa.String(), nullable=False),
        sa.Column("prioridade", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default="proposed", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index(
        "ix_argos_sector_frameworks_setor_status",
        "argos_sector_frameworks",
        ["setor", "status"],
    )

    op.create_table(
        "argos_analyses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("period", sa.String(), nullable=False),
        sa.Column("output", postgresql.JSONB(), nullable=False),
        sa.Column("tendencia", sa.String(), nullable=False),
        sa.Column("risco_credito", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_argos_analyses_company_id", "argos_analyses", ["company_id"])

    op.create_table(
        "argos_tracked_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("argos_companies.id"), nullable=False),
        sa.Column("categoria", sa.String(), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=False),
        sa.Column("first_seen_analysis_id", sa.Integer(), sa.ForeignKey("argos_analyses.id"), nullable=False),
        sa.Column("last_seen_analysis_id", sa.Integer(), sa.ForeignKey("argos_analyses.id"), nullable=False),
        sa.Column("status", sa.String(), server_default="aberto", nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_argos_tracked_flags_company_id", "argos_tracked_flags", ["company_id"])

    op.create_table(
        "argos_sector_agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("argos_analyses.id"), nullable=False),
        sa.Column("setor", sa.String(), nullable=False),
        sa.Column("raw_output", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("argos_sector_agent_runs")
    op.drop_table("argos_tracked_flags")
    op.drop_table("argos_analyses")
    op.drop_table("argos_sector_frameworks")
    op.drop_table("argos_sector_knowledge")
    op.drop_table("argos_debt_maturities")
    op.drop_table("argos_operational_data")
    op.drop_table("argos_financial_indicators")
    op.drop_table("argos_financial_statements")
    op.drop_table("argos_companies")
