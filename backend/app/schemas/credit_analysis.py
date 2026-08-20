from typing import Literal

from pydantic import BaseModel

# Diferencia fato/calculo/estimativa/interpretacao/hipotese em cada afirmacao
# relevante, para nunca misturar dado real com inferencia sem sinalizar isso.
# Port 1:1 de schemas/analysisOutput.ts (Argos legado).
ClaimKind = Literal["fato", "calculo", "estimativa", "interpretacao", "hipotese"]


class Claim(BaseModel):
    texto: str
    tipo: ClaimKind


class RiscoCredito(BaseModel):
    nivel: Literal["baixo", "moderado", "elevado", "critico"]
    justificativa: str


class AnalysisOutput(BaseModel):
    """Contrato de saida da analise final do Master - as 14 secoes pedidas."""

    resumo_executivo: str
    o_que_mudou: list[Claim]
    financeiro: list[Claim]
    caixa: list[Claim]
    endividamento_liquidez: list[Claim]
    visao_setorial: list[Claim]
    pontos_positivos: list[Claim]
    pontos_atencao: list[Claim]
    red_flags: list[Claim]
    tendencia: Literal["melhora", "estavel", "deteriorando"]
    risco_credito: RiscoCredito
    o_que_monitorar: list[str]
    dados_faltantes: list[str]
    conclusao: str
