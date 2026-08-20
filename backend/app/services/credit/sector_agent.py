"""Especialista de credito setorial: monta o prompt do especialista a partir
de duas fontes que evoluem separadamente - argos_sector_knowledge
(conhecimento qualitativo) e argos_sector_frameworks com status='active'
(metricas oficialmente monitoradas) - e roda a tarefa agentica via
AIProvider, devolvendo uma LEITURA setorial (texto) para o Master consumir
como insumo, nunca como veredito de credito.

Port de agents/sectors/registry.ts (Argos legado). O legado usava um
AgentDefinition por setor (subagente do Claude Agent SDK, invocado pelo
Master via a tool "Task"); aqui nao ha equivalente de plataforma para
subagentes declarativos, entao o Master invoca isto diretamente atraves de
uma tool propria ("consult_sector_specialist", ver master_agent.py) que
chama run_sector_specialist().
"""

import re
import unicodedata

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.repositories import credit_repository as repo
from app.schemas.sector_knowledge import SectorKnowledge
from app.services.ai_provider.base import AIProvider
from app.services.credit.tool_registry import execute_tool, get_tool_definitions

SECTOR_SPECIALIST_TOOL_NAMES = [
    "get_company_profile",
    "get_financial_statements",
    "get_financial_indicators",
    "get_operational_data",
    "get_debt_schedule",
    "diff_periods",
    "get_sector_framework",
    "propose_metric",
]

SECTOR_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "texto": {
            "type": "string",
            "description": (
                "Leitura setorial objetiva e estruturada pela cadeia de raciocinio causal "
                "(o que aconteceu -> por que -> operacional -> financeiro -> caixa -> credito), "
                "sempre citando de qual metrica/dado e periodo cada afirmacao vem. Nunca as 14 "
                "secoes finais nem uma conclusao de risco de credito - isso e exclusivo do Master."
            ),
        }
    },
    "required": ["texto"],
}


class SectorSpecialistOutput(BaseModel):
    texto: str


def slugify_sector(setor: str) -> str:
    normalized = unicodedata.normalize("NFD", setor)
    without_diacritics = "".join(c for c in normalized if unicodedata.category(c) != "Mn")
    slug = re.sub(r"[^a-z0-9]+", "-", without_diacritics.lower())
    return "sector-" + slug.strip("-")


def _format_knowledge_section(knowledge: SectorKnowledge) -> str:
    riscos = "\n".join(f"  - {r.nome}: {r.descricao}" for r in knowledge.riscos_caracteristicos)
    causais = "\n".join(
        f"  - {r.evento}\n"
        f"      operacional: {r.impacto_operacional}\n"
        f"      financeiro: {r.impacto_financeiro}\n"
        f"      caixa: {r.impacto_caixa}\n"
        f"      alavancagem/liquidez: {r.impacto_alavancagem_liquidez}\n"
        f"      credito: {r.impacto_credito}"
        for r in knowledge.relacoes_causais
    )
    red_flags = "\n".join(f"  - {f}" for f in knowledge.red_flags)
    contexto = "\n".join(f"  - {c}" for c in knowledge.contexto_externo)
    monitoramento = "\n".join(f"  - {m}" for m in knowledge.monitoramento_continuo)
    indicadores = "\n".join(f"  - {i}" for i in knowledge.indicadores_operacionais_tipicos)

    return f"""## Conhecimento do setor "{knowledge.setor}"

**Modelo de negocio:** {knowledge.modelo_de_negocio}
**Formacao de receita:** {knowledge.formacao_receita}
**Estrutura de custos e precificacao:** {knowledge.estrutura_custos_e_precificacao}
**Margens:** {knowledge.margens}
**Capital de giro e ciclos:** {knowledge.capital_de_giro_e_ciclos}
**Oferta, demanda e regulacao:** {knowledge.oferta_demanda_e_regulacao}
**CAPEX e necessidade de financiamento:** {knowledge.capex_e_necessidade_financiamento}

**Principais riscos caracteristicos:**
{riscos}

**Relacoes causais tipicas (evento/driver -> operacional -> financeiro -> caixa -> alavancagem/liquidez -> credito):**
{causais}

**Red flags (sinais antecedentes de deterioracao de credito):**
{red_flags}

**Contexto externo necessario para explicar os numeros:**
{contexto}

**O que monitorar continuamente:**
{monitoramento}

**Indicadores operacionais tipicos do setor:**
{indicadores}"""


def build_sector_agent_prompt(setor: str, knowledge: SectorKnowledge | None) -> str:
    if knowledge is not None:
        knowledge_section = _format_knowledge_section(knowledge)
    else:
        knowledge_section = (
            f'Nenhum conhecimento setorial estruturado foi cadastrado ainda para "{setor}" - '
            "baseie-se no que os proprios dados da empresa permitirem observar e seja explicito "
            'sobre essa limitacao (registre em "Dados Faltantes"/observacoes, nao estime silenciosamente).'
        )

    return f"""Voce e o analista de credito senior especialista no setor "{setor}" do Argos. Sua funcao e interpretar os fatores especificos desta industria para apoiar a conclusao do Agente Master. Voce e um INSUMO para a decisao do Master - nunca determina o risco de credito final da empresa, isso e responsabilidade exclusiva dele.

{knowledge_section}

Como voce deve raciocinar - NUNCA pare em "metrica -> variacao -> conclusao":
1. O que aconteceu: descreva o fato observado nos dados (get_financial_statements, get_financial_indicators, get_operational_data, get_debt_schedule), sempre citando metrica e periodo.
2. Por que aconteceu: busque a causa usando o conhecimento do setor acima e os dados disponiveis.
3. Consequencia operacional: o que isso significa para a operacao da empresa dentro da dinamica deste setor.
4. Consequencia financeira: como isso se reflete em receita, margem ou custo.
5. Impacto no caixa: como isso afeta geracao ou consumo de caixa.
6. Impacto no credito: como isso afeta a capacidade de pagamento - mas apresente isso como uma LEITURA setorial para o Master avaliar, nao como veredito.

Se a causa nao puder ser comprovada pelos dados disponiveis, classifique-a explicitamente como hipotese - nunca a apresente como fato. Marque toda afirmacao relevante com seu tipo (fato / calculo / estimativa / interpretacao / hipotese), do mesmo jeito que o Master faz na analise final.

Regras de trabalho:
- Chame get_sector_framework(setor="{setor}", company_id=<id da empresa>) para saber quais metricas o Argos monitora oficialmente para este setor (defaults do setor + eventuais metricas especificas desta empresa). Se vier vazio, diga isso explicitamente e nao invente que existe um framework ativo - continue sua analise apoiado no seu conhecimento setorial e nos dados brutos disponiveis, e considere propor as metricas que faltam.
- Para cada metrica do framework marcada como Essencial ou Relevante, busque o valor correspondente via get_financial_statements, get_financial_indicators, get_operational_data ou get_debt_schedule, conforme a fonte ideal indicada, e use diff_periods para variacoes entre periodos - nunca calcule variacao de cabeca.
- Voce nao esta limitado as metricas cadastradas: se perceber, com base no seu conhecimento do setor, algo relevante para credito que nenhuma metrica atual do framework captura, use propose_metric para sugerir a inclusao. Isso fica pendente de revisao humana e nao altera o framework ativo - voce nunca ativa uma metrica sozinho.
- Devolva ao Master uma leitura setorial objetiva e estruturada pela cadeia de raciocinio causal acima, sempre citando de qual metrica/dado e periodo cada afirmacao vem - nunca as 14 secoes finais nem uma conclusao de risco de credito; isso e exclusivo do Master."""


def list_available_sectors(db: Session) -> list[str]:
    """Setores com especialista disponivel: tem conhecimento qualitativo
    cadastrado OU framework de metricas ativo (ou ambos) - cadastrar uma
    linha em qualquer uma das duas fontes ja disponibiliza (ou enriquece)
    um especialista, sem tocar em codigo."""
    knowledge_sectors = {row.setor for row in repo.list_sector_knowledge(db)}
    framework_sectors = set(repo.list_active_framework_sectors(db))
    return sorted(knowledge_sectors | framework_sectors)


def run_sector_specialist(db: Session, provider: AIProvider, setor: str, company_id: int) -> str:
    knowledge_row = repo.get_sector_knowledge(db, setor)
    knowledge = SectorKnowledge(setor=setor, **knowledge_row.content) if knowledge_row else None

    system_prompt = build_sector_agent_prompt(setor, knowledge)
    user_prompt = (
        f'Analise a empresa (id={company_id}) sob a perspectiva do setor "{setor}". '
        "Siga rigorosamente a sequencia de raciocinio do seu system prompt."
    )
    tools = get_tool_definitions(SECTOR_SPECIALIST_TOOL_NAMES)

    def tool_executor(name: str, tool_input: dict) -> dict:
        return execute_tool(db, name, tool_input)

    raw_result = provider.run_agentic_task(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        tools=tools,
        tool_executor=tool_executor,
        output_schema=SECTOR_OUTPUT_SCHEMA,
    )
    return SectorSpecialistOutput.model_validate(raw_result).texto
