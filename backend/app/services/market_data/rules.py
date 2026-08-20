"""Ponto de chamada do motor de regras de mercado (alertas/thresholds sobre
argos_metrics) - ainda NAO implementado. run_daily_update() ja chama esta
funcao apos recalcular as metricas, entao ligar regras reais no futuro exige
mudar so o corpo desta funcao, nao o fluxo do job.
"""

from sqlalchemy.orm import Session


def run_market_rules(db: Session) -> dict:
    return {"status": "not_implemented", "detail": "motor de regras de mercado ainda nao existe"}
