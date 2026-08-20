"""Abstracao do provedor de LLM por tras dos agentes de credito (Master de
Credito, especialistas setoriais).

Nenhum codigo do dominio de credito (app/services/credit/*) deve importar um
SDK de LLM especifico (anthropic, openai, ...) diretamente - so o contrato
deste modulo. Troca de provedor/modelo = nova implementacao de AIProvider,
zero mudanca no dominio de credito:

    Argos (dominio de credito) -> AIProvider -> Claude / OpenAI / outro

Isso preserva o papel que o @anthropic-ai/claude-agent-sdk cumpria no Argos
legado (query() com tools + outputFormat: json_schema), mas sem acoplar o
dominio a esse SDK especifico - nenhum provider concreto foi ainda ligado
a uma API real (ver AnthropicProvider, propositalmente nao implementado
ainda: falta decidir SDK/modelo/API key com o usuario).
"""

from abc import ABC, abstractmethod
from typing import Any, Callable

# (tool_name, tool_input) -> tool_result (dict JSON-serializavel)
ToolExecutor = Callable[[str, dict[str, Any]], dict[str, Any]]


class AIProviderError(RuntimeError):
    """Levantado quando o provider nao consegue completar a tarefa agentica
    (ex: esgotou max_turns sem submeter uma saida estruturada valida, ou a
    chamada ao modelo falhou)."""


class AIProvider(ABC):
    @abstractmethod
    def run_agentic_task(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]],
        tool_executor: ToolExecutor,
        output_schema: dict[str, Any],
        max_turns: int = 20,
    ) -> dict[str, Any]:
        """Roda um loop agentic completo: envia o prompt, executa toda tool
        chamada pelo modelo via `tool_executor(name, input) -> dict`, e
        retorna a saida final estruturada como dict (ainda nao validada
        contra um schema Pydantic - isso e responsabilidade de quem chama)
        assim que o modelo submeter um resultado conforme `output_schema`
        (JSON Schema).

        A implementacao concreta decide COMO forcar essa saida final (ex:
        uma tool sintetica "submit_result" cujo input_schema e
        `output_schema`, chamada obrigatoriamente ao final) - esse detalhe de
        wire format e responsabilidade do provider, nunca do dominio.

        Deve levantar AIProviderError se o modelo esgotar max_turns sem
        submeter uma saida estruturada.
        """
        raise NotImplementedError
