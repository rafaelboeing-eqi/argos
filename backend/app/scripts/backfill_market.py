"""Manual backfill for argos_market_history. Never run automatically.

Usage examples:

    python -m app.scripts.backfill_market --macro --start-date 2024-01-01
    python -m app.scripts.backfill_market --futures-asset DI1 --start-date 2025-01-01
    python -m app.scripts.backfill_market --asset BGI --symbol BGIQ26 --start-date 2025-01-01
    python -m app.scripts.backfill_market --treasury-asset treasury_ipca --start-date 2025-01-01

At least one of --macro, --futures-asset, --symbol or --treasury-asset is
required - the script does nothing by default so it can't be run unattended
by accident.
"""

import argparse
import json
import sys
from datetime import date

from app.core.database import SessionLocal
from app.services.market_data.config import FUTURES_ASSETS, TREASURY_ASSETS, TREASURY_HISTORY_BATCH_SIZE
from app.services.market_data.market_collector import MarketCollectorService, chunked


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--futures-asset",
        choices=FUTURES_ASSETS,
        help="Backfill history for every contract currently quoted in this asset's curve",
    )
    parser.add_argument("--symbol", help="Backfill history for one specific futures contract symbol")
    parser.add_argument(
        "--asset",
        choices=FUTURES_ASSETS,
        help="Underlying asset for --symbol (required together with --symbol)",
    )
    parser.add_argument("--macro", action="store_true", help="Backfill the configured macro series")
    parser.add_argument(
        "--treasury-asset",
        choices=TREASURY_ASSETS,
        help="Backfill history for every bond currently listed under this Tesouro Direto asset",
    )
    parser.add_argument("--start-date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end-date", help="YYYY-MM-DD, defaults to today")
    parser.add_argument("--sort-order", default="asc", choices=["asc", "desc"])
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not (args.futures_asset or args.symbol or args.macro or args.treasury_asset):
        parser.error("Specify at least one of --futures-asset, --symbol, --macro, or --treasury-asset")
    if args.symbol and not args.asset:
        parser.error("--symbol requires --asset")

    end_date = args.end_date or date.today().isoformat()

    if SessionLocal is None:
        print("Database is not configured (check backend/.env). Aborting.", file=sys.stderr)
        return 1

    results = []
    with SessionLocal() as db:
        collector = MarketCollectorService(db)

        if args.macro:
            results.append(
                collector.collect_macro_history(start_date=args.start_date, end_date=end_date, sort_order=args.sort_order)
            )

        if args.futures_asset:
            symbols = collector.discover_curve_symbols(args.futures_asset)
            if not symbols:
                results.append({"asset": args.futures_asset, "error": "no symbols found on current curve"})
            for symbol in symbols:
                results.append(
                    collector.collect_futures_history(
                        args.futures_asset, symbol, start_date=args.start_date, end_date=end_date, sort_order=args.sort_order
                    )
                )

        if args.symbol:
            results.append(
                collector.collect_futures_history(
                    args.asset, args.symbol, start_date=args.start_date, end_date=end_date, sort_order=args.sort_order
                )
            )

        if args.treasury_asset:
            bonds = collector.discover_treasury_bonds(args.treasury_asset)
            if not bonds:
                results.append({"asset": args.treasury_asset, "error": "no bonds found for this treasury asset"})
            symbols = [bond["symbol"] for bond in bonds if bond.get("symbol")]
            for batch in chunked(symbols, TREASURY_HISTORY_BATCH_SIZE):
                results.append(
                    collector.collect_treasury_history(
                        args.treasury_asset, batch, start_date=args.start_date, end_date=end_date, sort_order=args.sort_order
                    )
                )

    print(json.dumps(results, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
