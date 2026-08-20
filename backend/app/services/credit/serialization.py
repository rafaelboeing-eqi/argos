"""Serializacao generica de linhas ORM para dict JSON-serializavel - usada
pelas tools de credito, cujo retorno vai direto para o modelo (via tool_result)."""

from datetime import date, datetime
from decimal import Decimal


def row_to_dict(row) -> dict:
    result: dict = {}
    for column in row.__table__.columns:
        value = getattr(row, column.name)
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[column.name] = value
    return result
