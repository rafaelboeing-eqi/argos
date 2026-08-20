"""Execucao manual do job diario de atualizacao de mercado - para
desenvolvimento, ou para rodar sob demanda fora do horario agendado.

Usage:

    python -m app.scripts.run_daily_update

Chama exatamente a mesma funcao (run_daily_update) que
app/scripts/run_scheduler.py roda automaticamente todo dia - nao existe
comportamento especial de "modo manual" vs "modo agendado".
"""

import json
import sys

from app.core.database import SessionLocal
from app.services.market_data.daily_update import run_daily_update


def main() -> int:
    if SessionLocal is None:
        print("Database is not configured (check backend/.env). Aborting.", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        summary = run_daily_update(db)

    print(json.dumps(summary, indent=2, default=str))
    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
