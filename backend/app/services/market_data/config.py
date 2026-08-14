"""Single source of truth for which market instruments Argos monitors.

Nothing outside this module should hard-code an asset code, commodity label,
or macro slug — import from here instead.
"""

SOURCE_BRAPI = "brapi"

CATEGORY_FUTURES_CURVE = "futures_curve"
CATEGORY_MACRO = "macro"
CATEGORY_TREASURY = "treasury"

# B3 futures underlying assets collected by the MarketCollectorService.
FUTURES_ASSETS = [
    "DI1",
    "DAP",
    "BGI",
    "CCM",
    "ICF",
    "SJC",
]

# Assets quoted as a rate (%), where the relevant metric is settlementRate
# and variations are expressed in basis points.
RATE_CURVE_ASSETS = ["DI1", "DAP"]

# Assets quoted as a price, where the relevant metric is settlement/close
# and variations are expressed in percentage.
COMMODITY_ASSETS = ["BGI", "CCM", "ICF", "SJC"]

# Display label for each commodity, used by the frontend cards.
COMMODITY_LABELS = {
    "BGI": "Boi",
    "CCM": "Milho",
    "ICF": "Café",
    "SJC": "Soja",
}

# brapi macro slugs collected daily (see GET /api/v2/macro/available for the full catalog).
MACRO_SERIES = [
    "selic",
    "ipca",
]

# Macro slugs surfaced as top-of-page cards on /mercado.
MACRO_HIGHLIGHT_SERIES = [
    "selic",
    "ipca",
]

# Tesouro Direto asset codes collected. Each groups every bond (any maturity,
# any couponType) whose bondType starts with the matching prefix below - see
# TREASURY_BOND_TYPE_PREFIXES for why that's not the same as brapi's own
# `indexer` field (indexer=ipca also covers Tesouro Educa+ and Tesouro Renda+,
# which are out of scope here).
TREASURY_ASSETS = [
    "treasury_ipca",
    "treasury_prefixado",
    "treasury_selic",
]

TREASURY_BOND_TYPE_PREFIXES = {
    "treasury_ipca": "Tesouro IPCA+",
    "treasury_prefixado": "Tesouro Prefixado",
    "treasury_selic": "Tesouro Selic",
}

TREASURY_LABELS = {
    "treasury_ipca": "Tesouro IPCA+",
    "treasury_prefixado": "Tesouro Prefixado",
    "treasury_selic": "Tesouro Selic",
}

# brapi paginates GET /api/v2/treasury/list at 20 results/page by default (~60
# bonds exist across all indexers today) - pass a generous explicit limit so
# discovery never silently misses bonds past page 1.
TREASURY_LIST_LIMIT = 300

# Conservative batch size for GET /api/v2/treasury/indicators/history - brapi
# documents a ~20-bond cap for the sibling /treasury/indicators snapshot
# endpoint; applied here too since /history's own limit isn't documented.
TREASURY_HISTORY_BATCH_SIZE = 20
