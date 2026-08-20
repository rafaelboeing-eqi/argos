"""Ponto unico de extensao para plugar um AIProvider real nas rotas de
credito. Nenhuma decisao de SDK/modelo/API key foi tomada ainda - ver
app/services/ai_provider/base.py.

`get_ai_provider` retorna None enquanto isso nao for decidido (nunca levanta
excecao ao ser resolvido) para nao quebrar rotas que so PRECISAM de um
provider condicionalmente (ex: ingestao de dados que so dispara analise se
pedido) - quem precisa mesmo do provider chama `require_ai_provider` sobre o
resultado, que ai sim converte a ausencia em 503 com o motivo explicito.
"""

from fastapi import HTTPException

from app.services.ai_provider.base import AIProvider


def get_ai_provider() -> AIProvider | None:
    return None


def require_ai_provider(provider: AIProvider | None) -> AIProvider:
    if provider is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Nenhum AI Provider real esta configurado ainda para o dominio de credito. "
                "Decisao pendente: qual SDK instalar (anthropic, openai, ...), qual modelo usar "
                "e a API key correspondente - ver app/services/ai_provider/base.py e "
                "app/services/ai_provider/dependency.py."
            ),
        )
    return provider
