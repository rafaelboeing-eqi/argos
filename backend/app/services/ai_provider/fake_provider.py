"""Provider de teste - nao chama nenhum LLM real, nao depende de nenhum SDK
nem de ANTHROPIC_API_KEY. Existe para permitir testar o fluxo completo dos
agentes de credito (prompts, contratos, ordem de chamadas de tool, validacao
de saida) end-to-end antes de qualquer decisao de provedor/modelo real.
"""

from typing import Any

from app.services.ai_provider.base import AIProvider, ToolExecutor


class FakeAIProvider(AIProvider):
    """Roteiro fixo: executa (na ordem) as tool calls planejadas via o
    `tool_executor` real do chamador (portanto EXERCITA o dispatch de tools
    de verdade contra o banco), e por fim retorna `final_result` - simulando
    o "submit_result" que um provider real receberia do modelo."""

    def __init__(
        self,
        planned_tool_calls: list[tuple[str, dict[str, Any]]] | None = None,
        final_result: dict[str, Any] | None = None,
    ):
        self.planned_tool_calls = planned_tool_calls or []
        self.final_result = final_result if final_result is not None else {}
        self.executed_tool_calls: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
        self.received_system_prompt: str | None = None
        self.received_user_prompt: str | None = None

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
        self.received_system_prompt = system_prompt
        self.received_user_prompt = user_prompt
        for name, tool_input in self.planned_tool_calls:
            result = tool_executor(name, tool_input)
            self.executed_tool_calls.append((name, tool_input, result))
        return self.final_result
