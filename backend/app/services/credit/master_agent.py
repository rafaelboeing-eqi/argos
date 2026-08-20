"""Master de Credito: orquestra a analise completa de uma empresa - consulta
dados, delega ao especialista setorial correspondente, cruza as duas visoes
e produz a saida estruturada final (AnalysisOutput) via AIProvider.

Port de agents/master/runMasterAnalysis.ts + agents/master/systemPrompt.ts
(Argos legado). A delegacao ao especialista setorial usava a tool "Task" do
Claude Agent SDK (subagentes declarativos); aqui isso e substituido pela
tool "consult_sector_specialist", cujo handler chama
sector_agent.run_sector_specialist() diretamente - mesmo efeito (o Master
delega e recebe uma leitura setorial de volta), sem depender de nenhum
recurso de plataforma especifico de um SDK.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from app.schemas.credit_analysis import AnalysisOutput
from app.services.ai_provider.base import AIProvider
from app.services.credit.sector_agent import list_available_sectors, run_sector_specialist
from app.services.credit.tool_registry import execute_tool, get_tool_definitions

MASTER_TOOL_NAMES = [
    "get_company_profile",
    "get_financial_statements",
    "get_financial_indicators",
    "get_operational_data",
    "get_debt_schedule",
    "diff_periods",
    "get_sector_framework",
    "get_analysis_history",
    "get_tracked_flags",
    "propose_metric",
]

CONSULT_SECTOR_SPECIALIST_TOOL = {
    "name": "consult_sector_specialist",
    "description": (
        "Delega ao especialista de credito do setor informado para obter uma leitura setorial "
        "sobre a empresa em analise. O especialista devolve uma LEITURA (texto), nunca uma "
        "conclusao de credito - cabe a voce cruzar essa leitura com a analise financeira, nunca "
        "aceita-la automaticamente."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"setor": {"type": "string"}},
        "required": ["setor"],
    },
}


def build_master_system_prompt(sector_names: list[str]) -> str:
    especialistas = ", ".join(sector_names) if sector_names else "(nenhum cadastrado ainda)"
    return f"""Voce e o Agente Master de Credito do Argos. Seu foco e EXCLUSIVAMENTE risco de credito e capacidade de pagamento - nunca valuation de acoes ou recomendacao de investimento em equity.

Especialistas setoriais disponiveis: {especialistas}.

Ao analisar uma empresa, siga esta sequencia:

1. Consulte o cadastro da empresa (get_company_profile) - o setor ja vem cadastrado ali; nao tente adivinhar o setor por conta propria.
2. Consulte todo o historico disponivel: DRE, Balanco, Fluxo de Caixa (get_financial_statements), indicadores financeiros (get_financial_indicators), dados operacionais (get_operational_data), cronograma de divida e covenants (get_debt_schedule) e analises anteriores (get_analysis_history, get_tracked_flags).
3. Para comparacoes entre periodos e tendencias, use SEMPRE a tool diff_periods em vez de calcular variacoes de cabeca - isso evita erro aritmetico.
4. Avalie geracao de caixa, capital de giro, divida, alavancagem, liquidez, vencimentos e covenants.
5. Acione o especialista do setor correspondente (tool consult_sector_specialist, informando setor=<nome do setor cadastrado>) para obter a visao setorial. O especialista devolve uma LEITURA setorial, nao uma conclusao de credito - a visao setorial e insumo para a sua analise, nao algo que voce deve aceitar automaticamente.
6. Cruze a analise financeira (DRE, Balanco, Fluxo de Caixa, divida, covenants) com a visao setorial retornada pelo especialista. Se a visao financeira contradisser a visao setorial (ex.: o especialista le uma queda de receita como sazonalidade normal do setor, mas os dados de caixa/divida mostram deterioracao persistente, ou vice-versa), identifique e explique essa divergencia explicitamente na analise - nunca a esconda nem escolha uma das duas leituras silenciosamente.
7. Para toda mudanca material identificada em "O que Mudou", construa a relacao causal completa (evento/driver -> impacto operacional -> impacto financeiro -> impacto no caixa -> impacto na alavancagem/liquidez -> impacto no credito) em vez de apenas registrar a variacao numerica. Se a causa nao puder ser comprovada pelos dados disponiveis, classifique-a como hipotese.
8. Identifique pontos positivos, pontos de atencao e red flags. Para cada red flag ou ponto de atencao ja visto em analises anteriores (get_tracked_flags), diga explicitamente qual e o status atual: se confirmou, reverteu, permanece em aberto, ou - mesmo permanecendo aberto - se intensificou ou diminuiu de severidade desde a ultima analise.
9. Conclua se a capacidade de pagamento esta melhorando, estavel ou deteriorando, e o nivel de risco de credito.

Regras inegociaveis:
- Nunca invente dados. Toda metrica ou fato deve vir de uma chamada de tool. Se um dado necessario nao existir, registre-o em "Dados Faltantes" em vez de estimar silenciosamente.
- Em cada afirmacao relevante, marque o tipo: 'fato' (veio direto de uma tool), 'calculo' (resultado de diff_periods ou aritmetica simples sobre fatos), 'estimativa' (aproximacao quando o dado exato nao existe, deixe claro a base), 'interpretacao' (sua leitura sobre o que os fatos significam) ou 'hipotese' (possivel explicacao nao confirmada).
- Se a empresa entrou com um novo resultado, a secao "O que Mudou" e a mais importante: o que mudou desde a ultima analise, por que mudou (até onde os dados permitem saber, com a relacao causal completa) e qual o impacto no risco de credito.
- O especialista setorial pode propor metricas novas ou apontar lacunas do framework atual - isso e insumo valido, mas nunca substitui o seu cruzamento com os demonstrativos financeiros nem determina, por si so, o risco de credito final.
- Ao final, voce DEVE produzir a saida estruturada final com as 14 secoes exigidas pelo schema - nao responda em texto livre solto fora do schema."""


def build_master_user_prompt(company_name: str, company_id: int, setor: str, period: str | None) -> str:
    foco_periodo = f" com foco no periodo mais recente ({period})" if period else ""
    return (
        f'Analise a capacidade de pagamento e o risco de credito da empresa "{company_name}" '
        f'(id={company_id}, setor cadastrado="{setor}"){foco_periodo}. '
        "Siga rigorosamente a sequencia e as regras do seu system prompt."
    )


@dataclass
class MasterAnalysisResult:
    output: AnalysisOutput
    sector_consultations: list[tuple[str, str]] = field(default_factory=list)


def run_master_analysis(
    db: Session,
    provider: AIProvider,
    company_id: int,
    company_name: str,
    setor: str,
    period: str | None = None,
) -> MasterAnalysisResult:
    sector_names = list_available_sectors(db)
    system_prompt = build_master_system_prompt(sector_names)
    user_prompt = build_master_user_prompt(company_name, company_id, setor, period)
    tools = get_tool_definitions(MASTER_TOOL_NAMES) + [CONSULT_SECTOR_SPECIALIST_TOOL]

    sector_consultations: list[tuple[str, str]] = []

    def tool_executor(name: str, tool_input: dict) -> dict:
        if name == "consult_sector_specialist":
            setor_consultado = tool_input["setor"]
            texto = run_sector_specialist(db, provider, setor_consultado, company_id)
            sector_consultations.append((setor_consultado, texto))
            return {"setor": setor_consultado, "leitura_setorial": texto}
        return execute_tool(db, name, tool_input)

    raw_result = provider.run_agentic_task(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=tools,
        tool_executor=tool_executor,
        output_schema=AnalysisOutput.model_json_schema(),
    )
    output = AnalysisOutput.model_validate(raw_result)
    return MasterAnalysisResult(output=output, sector_consultations=sector_consultations)
