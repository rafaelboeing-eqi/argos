"""Registro central das tools de credito - une financial_tools e history_tools
num unico dispatcher, usado pelo loop de tool-use do Master e dos especialistas
setoriais (master_agent.py, sector_agent.py).
"""

from typing import Any, Callable

from sqlalchemy.orm import Session

from app.services.credit.financial_tools import FINANCIAL_TOOLS
from app.services.credit.history_tools import HISTORY_TOOLS

_ALL_TOOLS: list[tuple[dict, Callable[[Session, dict[str, Any]], dict]]] = [*FINANCIAL_TOOLS, *HISTORY_TOOLS]

_DEFINITIONS_BY_NAME: dict[str, dict] = {definition["name"]: definition for definition, _ in _ALL_TOOLS}
_HANDLERS_BY_NAME: dict[str, Callable[[Session, dict[str, Any]], dict]] = {
    definition["name"]: handler for definition, handler in _ALL_TOOLS
}

ALL_TOOL_NAMES = list(_DEFINITIONS_BY_NAME.keys())


def get_tool_definitions(names: list[str]) -> list[dict]:
    """Definicoes (JSON Schema) das tools cujo nome esta em `names`, na ordem
    de `names`. Permite restringir o toolset por agente (ex: o Master nao
    tem acesso a propose_metric, so os especialistas setoriais tem)."""
    return [_DEFINITIONS_BY_NAME[name] for name in names]


def execute_tool(db: Session, name: str, input: dict[str, Any]) -> dict:
    handler = _HANDLERS_BY_NAME.get(name)
    if handler is None:
        return {"erro": f"tool desconhecida: {name}"}
    return handler(db, input)
