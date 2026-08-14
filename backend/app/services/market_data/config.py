"""Single source of truth for which market instruments Argos monitors.

Nothing outside this module should hard-code an asset code, commodity label,
or macro slug — import from here instead.
"""

SOURCE_BRAPI = "brapi"

CATEGORY_FUTURES_CURVE = "futures_curve"
CATEGORY_MACRO = "macro"

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
