"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";

import { ApiError, fetchJson } from "@/lib/api";
import { companyRiskStatus } from "@/lib/creditAggregation";
import type { AnalysisRecord, Company, CreditMetric, DebtMaturity, FinancialStatement, TrackedFlag } from "@/types/credit";
import { CreditMetricsChart } from "@/components/credit/CreditMetricsChart";
import { FinancialStatementsTable } from "@/components/credit/FinancialStatementsTable";
import { DebtScheduleTable } from "@/components/credit/DebtScheduleTable";
import { TrackedFlagsList } from "@/components/credit/TrackedFlagsList";
import { TriggerAnalysisPanel } from "@/components/credit/TriggerAnalysisPanel";
import { AnalysisHistoryList } from "@/components/credit/AnalysisHistoryList";
import { EmptyState } from "@/components/ui/EmptyState";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { SectionHeader } from "@/components/ui/SectionHeader";

const TABS = ["Visão Geral", "Financeiro", "Dívida", "Eventos", "Regras e Alertas", "Histórico", "Análises"] as const;
type Tab = (typeof TABS)[number];

export default function EmpresaDetailPage() {
  const params = useParams<{ id: string }>();
  const companyId = Number(params.id);

  const [company, setCompany] = useState<Company | null>(null);
  const [statements, setStatements] = useState<FinancialStatement[]>([]);
  const [metrics, setMetrics] = useState<CreditMetric[]>([]);
  const [debts, setDebts] = useState<DebtMaturity[]>([]);
  const [flags, setFlags] = useState<TrackedFlag[]>([]);
  const [analyses, setAnalyses] = useState<AnalysisRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [tab, setTab] = useState<Tab>("Visão Geral");

  useEffect(() => {
    if (!Number.isFinite(companyId)) return;
    let cancelled = false;

    Promise.all([
      fetchJson<Company>(`/api/companies/${companyId}`),
      fetchJson<FinancialStatement[]>(`/api/companies/${companyId}/financial-statements`),
      fetchJson<CreditMetric[]>(`/api/companies/${companyId}/credit-metrics`),
      fetchJson<DebtMaturity[]>(`/api/companies/${companyId}/debt-schedule`),
      fetchJson<TrackedFlag[]>(`/api/companies/${companyId}/tracked-flags`),
      fetchJson<AnalysisRecord[]>(`/api/companies/${companyId}/analyses`),
    ])
      .then(([companyData, statementsData, metricsData, debtsData, flagsData, analysesData]) => {
        if (cancelled) return;
        setCompany(companyData);
        setStatements(statementsData);
        setMetrics(metricsData);
        setDebts(debtsData);
        setFlags(flagsData);
        setAnalyses(analysesData);
      })
      .catch((cause) => {
        if (cancelled) return;
        if (cause instanceof ApiError && cause.status === 404) setNotFound(true);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [companyId]);

  const reload = () => {
    Promise.all([
      fetchJson<TrackedFlag[]>(`/api/companies/${companyId}/tracked-flags`),
      fetchJson<AnalysisRecord[]>(`/api/companies/${companyId}/analyses`),
    ])
      .then(([flagsData, analysesData]) => {
        setFlags(flagsData);
        setAnalyses(analysesData);
      })
      .catch(() => {});
  };

  const proximoVencimento = useMemo(() => {
    const withDate = debts.filter((debt) => debt.vencimento);
    if (withDate.length === 0) return null;
    return [...withDate].sort((a, b) => (a.vencimento! < b.vencimento! ? -1 : 1))[0].vencimento;
  }, [debts]);

  const risk = useMemo(() => companyRiskStatus(flags), [flags]);

  if (loading) {
    return (
      <div className="px-8 py-6">
        <div className="h-40 animate-pulse rounded-xl bg-white/60" />
      </div>
    );
  }

  if (notFound || !company) {
    return (
      <div className="flex flex-col gap-4 px-8 py-6">
        <EmptyState title="Empresa não encontrada" description="Volte para o painel de empresas." />
        <Link href="/painel" className="text-sm font-medium text-argos-600 underline">
          ← Voltar ao painel
        </Link>
      </div>
    );
  }

  return (
    <div className="flex w-full flex-col gap-6 px-8 py-6">
      <Link href="/painel" className="text-xs font-medium text-argos-600 underline">
        ← Painel
      </Link>

      <header className="flex flex-wrap items-start justify-between gap-3 rounded-xl border border-argos-100 bg-white p-5">
        <div className="flex flex-col gap-1">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold text-argos-950">{company.nome}</h1>
            <StatusBadge tone={risk.tone}>{risk.label}</StatusBadge>
          </div>
          <p className="text-sm text-argos-600">
            Emissor · Setor: {company.setor}
            {company.grupo_economico ? ` · Grupo econômico: ${company.grupo_economico}` : ""}
            {company.ticker ? ` · ${company.ticker}` : ""}
          </p>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        <MetricCard label="Exposição" value="—" caption="Ainda não modelado" muted />
        <MetricCard label="Clientes" value="—" caption="Ainda não modelado" muted />
        <MetricCard label="Taxa" value="—" caption="Ainda não modelado" muted />
        <MetricCard label="Próximo vencimento" value={proximoVencimento ?? "—"} caption={proximoVencimento ? undefined : "Sem dívida cadastrada"} muted={!proximoVencimento} />
        <MetricCard label="Rating" value="—" caption="Ainda não modelado" muted />
      </section>

      <nav className="flex gap-1 overflow-x-auto border-b border-argos-100">
        {TABS.map((item) => (
          <button
            key={item}
            type="button"
            onClick={() => setTab(item)}
            className={`whitespace-nowrap border-b-2 px-3 py-2 text-sm font-medium transition ${
              tab === item ? "border-argos-400 text-argos-950" : "border-transparent text-argos-500 hover:text-argos-800"
            }`}
          >
            {item}
          </button>
        ))}
      </nav>

      {tab === "Visão Geral" && (
        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-3">
            <SectionHeader title="Indicadores de crédito" />
            <div className="rounded-xl border border-argos-100 bg-white p-5">
              <CreditMetricsChart metrics={metrics} />
            </div>
          </section>
          <section className="flex flex-col gap-3">
            <SectionHeader title="Regras e alertas" />
            <TrackedFlagsList flags={flags} />
          </section>
        </div>
      )}

      {tab === "Financeiro" && (
        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-3">
            <SectionHeader title="Indicadores de crédito" />
            <div className="rounded-xl border border-argos-100 bg-white p-5">
              <CreditMetricsChart metrics={metrics} />
            </div>
          </section>
          <section className="flex flex-col gap-3">
            <SectionHeader title="Demonstrativos financeiros" />
            <FinancialStatementsTable statements={statements} />
          </section>
        </div>
      )}

      {tab === "Dívida" && (
        <section className="flex flex-col gap-3">
          <SectionHeader title="Cronograma de dívida e covenants" />
          <DebtScheduleTable debts={debts} />
        </section>
      )}

      {tab === "Eventos" && (
        <section className="flex flex-col gap-3">
          <SectionHeader title="Eventos" />
          <EmptyState
            title="Eventos ainda não modelados"
            description="O Argos ainda não tem um registro estruturado de eventos corporativos (fatos relevantes, emissões, mudanças de rating externo etc.) para esta empresa."
          />
        </section>
      )}

      {tab === "Regras e Alertas" && (
        <section className="flex flex-col gap-3">
          <SectionHeader title="Red flags e pontos de atenção (Flag Tracker)" />
          <TrackedFlagsList flags={flags} />
        </section>
      )}

      {tab === "Histórico" && (
        <section className="flex flex-col gap-3">
          <SectionHeader title="Histórico de análises" />
          <AnalysisHistoryList analyses={analyses} />
        </section>
      )}

      {tab === "Análises" && (
        <div className="flex flex-col gap-6">
          <TriggerAnalysisPanel companyId={company.id} onAnalysisComplete={reload} />
          <section className="flex flex-col gap-3">
            <SectionHeader title="Análises anteriores" />
            <AnalysisHistoryList analyses={analyses} />
          </section>
        </div>
      )}
    </div>
  );
}
