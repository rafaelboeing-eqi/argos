from app.models.collection_run import ArgosCollectionRun
from app.repositories.collection_run_repository import list_runs_for_job
from app.services.market_data.config import FUTURES_ASSETS, TREASURY_ASSETS
from app.services.market_data.daily_update import run_daily_update
from app.services.market_data.exceptions import BrapiError
from app.services.market_data.market_collector import MarketCollectorService

DI1_TERM_STRUCTURE = {
    "asset": "DI1",
    "contracts": [
        {
            "symbol": "DI1U26",
            "expirationDate": "2026-09-01",
            "date": 1786579200,
            "settlementRate": 13.9,
        }
    ],
}

EMPTY_TERM_STRUCTURE = {"asset": "x", "contracts": []}

MACRO_LATEST = {
    "results": [
        {
            "series": {"slug": "selic", "unit": "percentPerYear", "frequency": "daily", "category": "interestRate", "name": "Selic"},
            "latest": {"date": "2026-08-14", "value": 14},
        }
    ]
}

# One bond per Tesouro Direto asset, so discover_treasury_bonds() finds a
# match for each of TREASURY_ASSETS instead of hitting the (unrelated)
# "no bonds found" branch in collect_treasury_curve_incremental().
TREASURY_LIST = {
    "results": [
        {
            "symbol": "tesouro-ipca-15082030",
            "bondType": "Tesouro IPCA+",
            "maturityDate": "2030-08-15",
            "baseDate": "2026-08-14",
            "buyRate": 6.5,
        },
        {
            "symbol": "tesouro-prefixado-01012029",
            "bondType": "Tesouro Prefixado",
            "maturityDate": "2029-01-01",
            "baseDate": "2026-08-14",
            "buyRate": 12.0,
        },
        {
            "symbol": "tesouro-selic-01032031",
            "bondType": "Tesouro Selic",
            "maturityDate": "2031-03-01",
            "baseDate": "2026-08-14",
            "buyRate": 0.1,
        },
    ]
}


class FakeProvider:
    """Todo ativo de futures retorna uma curva vazia (nao gera nenhum dado
    para persistir), exceto os listados em `failing_assets`, que levantam
    BrapiError - o suficiente para exercitar o isolamento de run_daily_update
    sem depender de um fixture completo por ativo."""

    def __init__(self, failing_assets: set[str] | None = None):
        self.failing_assets = failing_assets or set()

    def get_futures_term_structure(self, asset):
        if asset in self.failing_assets:
            raise BrapiError(f"fake failure for {asset}")
        return DI1_TERM_STRUCTURE if asset == "DI1" else EMPTY_TERM_STRUCTURE

    def get_macro_latest(self, symbols=None):
        return MACRO_LATEST

    def get_treasury_list(self, indexer=None, limit=None):
        return TREASURY_LIST

    def get_treasury_indicators_history(self, symbols, start_date=None, end_date=None, sort_order="asc"):
        return {"results": []}


def _patch_provider(monkeypatch, provider):
    monkeypatch.setattr(
        "app.services.market_data.daily_update.MarketCollectorService",
        lambda db: MarketCollectorService(db, provider=provider),
    )


def test_run_daily_update_runs_one_source_per_asset_plus_macro_metrics_and_rules(real_db_committable, monkeypatch):
    _patch_provider(monkeypatch, FakeProvider())

    summary = run_daily_update(real_db_committable)

    expected_sources = (
        [f"futures_curve:{asset}" for asset in FUTURES_ASSETS]
        + ["macro"]
        + [f"treasury:{asset}" for asset in TREASURY_ASSETS]
        + ["metrics", "rules"]
    )
    assert [s["source"] for s in summary["sources"]] == expected_sources
    assert summary["ok"] is True
    assert summary["failed_sources"] == []

    runs = list_runs_for_job(real_db_committable, summary["job_run_id"])
    assert len(runs) == len(expected_sources)
    assert all(run.status == "success" for run in runs)
    assert all(run.started_at is not None and run.finished_at is not None for run in runs)


def test_run_daily_update_isolates_a_failing_source_and_keeps_going(real_db_committable, monkeypatch):
    _patch_provider(monkeypatch, FakeProvider(failing_assets={"DAP"}))

    summary = run_daily_update(real_db_committable)

    assert summary["ok"] is False
    assert summary["failed_sources"] == ["futures_curve:DAP"]

    by_source = {s["source"]: s for s in summary["sources"]}
    assert by_source["futures_curve:DAP"]["status"] == "error"
    assert "fake failure for DAP" in by_source["futures_curve:DAP"]["error"]
    # Every other source still ran, including ones scheduled after the failure.
    assert by_source["futures_curve:DI1"]["status"] == "success"
    assert by_source["macro"]["status"] == "success"
    assert by_source["metrics"]["status"] == "success"
    assert by_source["rules"]["status"] == "success"

    failed_run = (
        real_db_committable.query(ArgosCollectionRun)
        .filter_by(job_run_id=summary["job_run_id"], source="futures_curve:DAP")
        .one()
    )
    assert failed_run.status == "error"
    assert failed_run.error is not None


def test_run_daily_update_survives_an_unexpected_exception_not_just_brapi_errors(real_db_committable, monkeypatch):
    class ExplodingProvider(FakeProvider):
        def get_futures_term_structure(self, asset):
            if asset == "BGI":
                raise RuntimeError("bug de verdade, nao um BrapiError")
            return super().get_futures_term_structure(asset)

    _patch_provider(monkeypatch, ExplodingProvider())

    summary = run_daily_update(real_db_committable)

    assert summary["failed_sources"] == ["futures_curve:BGI"]
    by_source = {s["source"]: s for s in summary["sources"]}
    assert "bug de verdade" in by_source["futures_curve:BGI"]["error"]
    # Sources scheduled after the buggy one still ran.
    assert by_source["treasury:treasury_ipca"]["status"] == "success"
    assert by_source["metrics"]["status"] == "success"
