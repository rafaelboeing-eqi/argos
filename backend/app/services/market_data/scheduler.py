"""Entry point for the daily market data job.

This module does NOT schedule anything itself - no cron, no background thread.
It only exposes collect_daily_market_data() so it can be wired later into
whatever runs scheduled jobs (cron, a task scheduler, company infra, ...).
"""

import logging

from sqlalchemy.orm import Session

from app.services.market_data.market_collector import MarketCollectorService
from app.services.market_data.market_metrics import MarketMetricsService

logger = logging.getLogger("argos.market_data.scheduler")


def collect_daily_market_data(db: Session) -> dict:
    """Fetch today's futures curves + latest macro observations, then recompute metrics.

    Safe to call at most once a day: it only asks brapi for the *current* snapshot
    (term-structure / macro latest), never full history.
    """
    collector = MarketCollectorService(db)

    curve_results = collector.collect_all_futures_curves()
    macro_result = collector.collect_macro_latest()

    metrics_counts = MarketMetricsService(db).compute_all()

    summary = {
        "curves": curve_results,
        "macro": macro_result,
        "metrics": metrics_counts,
    }
    logger.info("collect_daily_market_data finished: %s", summary)
    return summary
