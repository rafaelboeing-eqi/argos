"use client";

import { useState } from "react";

import { ApiError, postJson } from "@/lib/api";
import type { AnalysisOutput, TriggerAnalysisResponse } from "@/types/credit";

type PanelState = "idle" | "loading" | "done" | "error" | "no-provider";

export function TriggerAnalysisPanel({
  companyId,
  onAnalysisComplete,
}: {
  companyId: number;
  onAnalysisComplete?: () => void;
}) {
  const [state, setState] = useState<PanelState>("idle");
  const [result, setResult] = useState<AnalysisOutput | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const run = async () => {
    setState("loading");
    setErrorMessage(null);
    try {
      const response = await postJson<TriggerAnalysisResponse>(`/api/companies/${companyId}/analyses`, {});
      setResult(response.output);
      setState("done");
      onAnalysisComplete?.();
    } catch (cause) {
      if (cause instanceof ApiError && cause.status === 503) {
        setState("no-provider");
      } else {
        setState("error");
        setErrorMessage(cause instanceof Error ? cause.message : String(cause));
      }
    }
  };

  return (
    <div className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-argos-100">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-base font-semibold text-argos-950">Análise de crédito (Master Agent)</h2>
        <button
          type="button"
          onClick={run}
          disabled={state === "loading"}
          className="rounded-full bg-argos-400 px-4 py-2 text-sm font-medium text-white transition hover:bg-argos-500 disabled:opacity-50"
        >
          {state === "loading" ? "Analisando..." : "Rodar análise"}
        </button>
      </div>

      {state === "no-provider" && (
        <p className="rounded-xl bg-amber-50 p-3 text-sm text-amber-800">
          Nenhum AI Provider real está configurado ainda para o domínio de crédito — decisão de SDK/modelo/API key
          pendente. O Master Agent e os especialistas setoriais já existem e passam nos testes com um provider de
          teste, mas a análise real ainda não pode rodar em produção.
        </p>
      )}

      {state === "error" && errorMessage && (
        <p className="rounded-xl bg-red-50 p-3 text-sm text-red-800">{errorMessage}</p>
      )}

      {state === "done" && result && (
        <div className="flex flex-col gap-3 text-sm">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium uppercase tracking-wide text-argos-500">Risco de crédito</span>
            <span className="rounded-full bg-argos-100 px-2 py-0.5 text-xs font-medium text-argos-800">
              {result.risco_credito.nivel} · {result.tendencia}
            </span>
          </div>
          <p className="text-argos-950">{result.resumo_executivo}</p>
          <p className="text-argos-600">{result.conclusao}</p>
        </div>
      )}
    </div>
  );
}
