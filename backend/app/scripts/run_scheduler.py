"""Processo de longa duracao que roda run_daily_update() uma vez por dia, no
horario configurado por DAILY_UPDATE_TIME (HH:MM, hora local deste processo -
ver backend/.env.example). Nao tem estado proprio e nao depende do servidor
web (uvicorn) estar de pe nem de ninguem abrir o site - so precisa continuar
rodando (ex: systemd, pm2, screen/tmux, ou um servico gerenciado equivalente).

Usage:

    python -m app.scripts.run_scheduler

Loop simples e sem dependencias externas (sem cron, sem APScheduler): calcula
quantos segundos faltam para o proximo HH:MM configurado, dorme, roda o job,
repete. Se o processo cair, so falta reinicia-lo - nenhum estado precisa ser
recuperado, ja que run_daily_update() e incremental/idempotente por
construcao (ver market_collector.py).
"""

import logging
import sys
import time
from datetime import datetime, timedelta

from app.core.config import get_settings
from app.core.database import SessionLocal
from app.services.market_data.daily_update import run_daily_update

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger("argos.market_data.run_scheduler")


def _parse_hh_mm(value: str) -> tuple[int, int]:
    hour_str, _, minute_str = value.partition(":")
    return int(hour_str), int(minute_str)


def seconds_until_next_run(now: datetime, hour: int, minute: int) -> float:
    target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def run_forever() -> int:
    settings = get_settings()
    if SessionLocal is None:
        print("Database is not configured (check backend/.env). Aborting.", file=sys.stderr)
        return 1

    try:
        hour, minute = _parse_hh_mm(settings.daily_update_time)
    except ValueError:
        print(
            f"DAILY_UPDATE_TIME invalido: {settings.daily_update_time!r} (esperado 'HH:MM')",
            file=sys.stderr,
        )
        return 1

    logger.info("Scheduler iniciado - atualizacao diaria agendada para %02d:%02d (hora local)", hour, minute)

    while True:
        wait_seconds = seconds_until_next_run(datetime.now(), hour, minute)
        logger.info("Proxima atualizacao em %.1f minutos", wait_seconds / 60)
        time.sleep(wait_seconds)

        logger.info("Iniciando atualizacao diaria agendada")
        try:
            with SessionLocal() as db:
                summary = run_daily_update(db)
            if summary["ok"]:
                logger.info("Atualizacao diaria concluida sem falhas (job_run_id=%s)", summary["job_run_id"])
            else:
                logger.warning(
                    "Atualizacao diaria concluida com falhas em: %s (job_run_id=%s)",
                    summary["failed_sources"],
                    summary["job_run_id"],
                )
        except Exception:
            # run_daily_update() ja isola cada fonte - chegar aqui e algo fora
            # do previsto (ex: banco fora do ar). Loga e tenta de novo no
            # proximo horario agendado, em vez de derrubar o processo.
            logger.exception("Atualizacao diaria agendada falhou de forma inesperada")


if __name__ == "__main__":
    raise SystemExit(run_forever())
