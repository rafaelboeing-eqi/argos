from pydantic import BaseModel

# Port 1:1 de schemas/sectorKnowledge.ts (Argos legado).


class CausalRelation(BaseModel):
    """Uma relacao causal setorial: evento/driver -> cadeia de consequencias
    ate o credito. E o que separa um especialista de "metrica -> variacao ->
    conclusao" de um analista que entende POR QUE a metrica se moveu."""

    evento: str
    impacto_operacional: str
    impacto_financeiro: str
    impacto_caixa: str
    impacto_alavancagem_liquidez: str
    impacto_credito: str


class SectorRisk(BaseModel):
    nome: str
    descricao: str


class SectorKnowledgeContent(BaseModel):
    """Conhecimento setorial: tudo que um analista de credito senior
    especializado no setor precisa dominar sobre a dinamica do NEGOCIO.
    Deliberadamente separado do framework de metricas (sector_framework.py) -
    o conhecimento pode ser amplo e qualitativo; as metricas efetivamente
    monitoradas continuam governadas por proposed -> active -> deprecated.

    Separado de SectorKnowledge (que adiciona `setor`) para permitir um
    schema de entrada de rota sem o campo `setor` (ja vem na URL) - port do
    `sectorKnowledgeSchema.omit({setor: true})` do legado."""

    modelo_de_negocio: str
    formacao_receita: str
    estrutura_custos_e_precificacao: str
    margens: str
    capital_de_giro_e_ciclos: str
    oferta_demanda_e_regulacao: str
    capex_e_necessidade_financiamento: str
    riscos_caracteristicos: list[SectorRisk]
    relacoes_causais: list[CausalRelation]
    red_flags: list[str]
    contexto_externo: list[str]
    monitoramento_continuo: list[str]
    indicadores_operacionais_tipicos: list[str]


class SectorKnowledge(SectorKnowledgeContent):
    setor: str
