export type Company = {
  id: number;
  nome: string;
  cnpj: string | null;
  ticker: string | null;
  setor: string;
  grupo_economico: string | null;
  created_at: string;
};

export type FinancialStatement = {
  id: number;
  company_id: number;
  period: string;
  period_type: string;
  statement_type: "DRE" | "BALANCO" | "FLUXO_CAIXA";
  receita_liquida: number | null;
  ebitda: number | null;
  lucro_liquido: number | null;
  divida_bruta: number | null;
  divida_liquida: number | null;
  caixa: number | null;
  fonte: string | null;
  created_at: string;
};

export type CreditMetric = {
  period: string;
  receita_liquida: number | null;
  ebitda: number | null;
  lucro_liquido: number | null;
  divida_bruta: number | null;
  divida_liquida: number | null;
  caixa: number | null;
  margem_ebitda: number | null;
  margem_liquida: number | null;
  divida_liquida_ebitda: number | null;
  divida_bruta_ebitda: number | null;
  caixa_sobre_divida_bruta: number | null;
};

export type DebtMaturity = {
  id: number;
  company_id: number;
  descricao: string;
  vencimento: string | null;
  valor: number | null;
  covenant_descricao: string | null;
  covenant_status: "compliant" | "em_observacao" | "violado" | null;
  fonte: string | null;
  created_at: string;
};

export type TrackedFlag = {
  id: number;
  company_id: number;
  categoria: "ponto_atencao" | "red_flag";
  descricao: string;
  status: string;
  created_at: string;
  updated_at: string;
};

export type ClaimKind = "fato" | "calculo" | "estimativa" | "interpretacao" | "hipotese";

export type Claim = {
  texto: string;
  tipo: ClaimKind;
};

export type AnalysisOutput = {
  resumo_executivo: string;
  o_que_mudou: Claim[];
  financeiro: Claim[];
  caixa: Claim[];
  endividamento_liquidez: Claim[];
  visao_setorial: Claim[];
  pontos_positivos: Claim[];
  pontos_atencao: Claim[];
  red_flags: Claim[];
  tendencia: "melhora" | "estavel" | "deteriorando";
  risco_credito: { nivel: "baixo" | "moderado" | "elevado" | "critico"; justificativa: string };
  o_que_monitorar: string[];
  dados_faltantes: string[];
  conclusao: string;
};

export type TriggerAnalysisResponse = {
  analysis_id: number;
  output: AnalysisOutput;
};

export type AnalysisRecord = {
  id: number;
  company_id: number;
  period: string | null;
  output: AnalysisOutput;
  tendencia: AnalysisOutput["tendencia"];
  risco_credito: AnalysisOutput["risco_credito"];
  created_at: string;
};
