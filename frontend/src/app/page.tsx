"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";

import { fetchJson } from "@/lib/api";
import { fetchAllTrackedFlags, flagTone, OPEN_FLAG_STATUSES, type FlagWithCompany } from "@/lib/creditAggregation";
import { formatDate, formatDateTime, formatPercent } from "@/lib/format";
import type { Company } from "@/types/credit";
import type { MarketOverview } from "@/types/market";
import { MetricCard } from "@/components/ui/MetricCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { AlertCard } from "@/components/ui/AlertCard";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";

const STATUS_LABEL: Record<string, string> = {
  aberto: "Abertos",
  confirmado: "Confirmados",
  revertido: "Revertidos",
  resolvido: "Resolvidos",
};

const CATEGORIA_LABEL: Record<FlagWithCompany["categoria"], string> = {
  red_flag: "Red flag",
  ponto_atencao: "Ponto de atenção",
};

export default function InicialPage() {
  const [companies, setCompanies] = useState<Company[] | null>(null);
  const [flags, setFlags] = useState<FlagWithCompany[] | null>(null);
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    fetchJson<Company[]>("/api/companies")
      .then(async (companyList) => {
        if (cancelled) return;
        setCompanies(companyList);
        const allFlags = await fetchAllTrackedFlags(companyList);
        if (!cancelled) setFlags(allFlags);
      })
      .catch(() => {
        if (!cancelled) {
          setCompanies([]);
          setFlags([]);
        }
      });

    fetchJson<MarketOverview>("/api/market/overview")
      .then((data) => {
        if (!cancelled) setOverview(data);
      })
      .catch(() => {
        if (!cancelled) setOverview(null);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const openFlagsCount = useMemo(() => flags?.filter((flag) => OPEN_FLAG_STATUSES.has(flag.status)).length ?? 0, [flags]);
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = { aberto: 0, confirmado: 0, revertido: 0, resolvido: 0 };
    flags?.forEach((flag) => {
      counts[flag.status] = (counts[flag.status] ?? 0) + 1;
    });
    return counts;
  }, [flags]);
  const recentFlags = useMemo(() => flags?.slice(0, 8) ?? [], [flags]);
  const hasFlagHistory = (flags?.length ?? 0) > 0;

  const columns: DataTableColumn<FlagWithCompany>[] = [
    {
      key: "empresa",
      header: "Empresa / Setor",
      render: (flag) => (
        <div className="flex flex-col">
          <span className="font-medium text-argos-950">{flag.company.nome}</span>
          <span className="text-xs text-argos-500">{flag.company.setor}</span>
        </div>
      ),
    },
    { key: "tipo", header: "Tipo", render: (flag) => CATEGORIA_LABEL[flag.categoria] },
    { key: "descricao", header: "Descrição", render: (flag) => <span className="line-clamp-2">{flag.descricao}</span> },
    {
      key: "status",
      header: "Status",
      render: (flag) => <StatusBadge tone={flagTone(flag)}>{flag.status}</StatusBadge>,
    },
    { key: "atualizado", header: "Atualizado", render: (flag) => formatDateTime(flag.updated_at) },
    {
      key: "acao",
      header: "Ação",
      render: (flag) => (
        <Link href={`/empresas/${flag.company.id}`} className="text-xs font-medium text-argos-600 underline">
          Ver detalhes
        </Link>
      ),
    },
  ];

  return (
    <div className="flex w-full flex-col gap-6 px-8 py-6">
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <MetricCard label="Empresas monitoradas" value={companies === null ? "…" : String(companies.length)} />
        <MetricCard label="Exposição total" value="—" caption="Ainda não modelado no Argos" muted />
        <MetricCard label="Clientes impactados" value="—" caption="Ainda não modelado no Argos" muted />
        <MetricCard
          label="Riscos em atenção"
          value={flags === null ? "…" : String(openFlagsCount)}
          caption="Red flags e pontos de atenção abertos ou confirmados"
        />
      </section>

      <section className="flex flex-col gap-3 rounded-xl border border-argos-100 bg-white p-5">
        <SectionHeader title="O que mudou desde sua última visita" />
        {!hasFlagHistory ? (
          <EmptyState
            title="Nenhuma mudança registrada ainda"
            description="Assim que o Master Agent rodar análises e o Flag Tracker registrar red flags/pontos de atenção, as mudanças aparecem aqui."
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {(["aberto", "confirmado", "revertido", "resolvido"] as const).map((status) => (
              <div key={status} className="flex flex-col gap-1 rounded-lg border border-argos-50 p-3">
                <span className="text-xl font-semibold text-argos-950">{statusCounts[status]}</span>
                <span className="text-xs text-argos-500">{STATUS_LABEL[status]}</span>
              </div>
            ))}
          </div>
        )}
      </section>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <section className="flex flex-col gap-3 lg:col-span-2">
          <SectionHeader title="Principais movimentos" />
          {!hasFlagHistory ? (
            <EmptyState
              title="Nenhum movimento ainda"
              description="Cadastre empresas no Painel e rode análises para ver os movimentos de crédito aqui."
            />
          ) : (
            <DataTable columns={columns} rows={recentFlags} rowKey={(flag) => flag.id} />
          )}
        </section>

        <div className="flex flex-col gap-6">
          <section className="flex flex-col gap-2 rounded-xl border border-argos-100 bg-white p-5">
            <SectionHeader title="Alertas recentes" />
            {!hasFlagHistory ? (
              <EmptyState title="Sem alertas" description="Alertas aparecem aqui conforme os flags forem detectados." />
            ) : (
              <div className="flex flex-col">
                {recentFlags.slice(0, 5).map((flag) => (
                  <AlertCard
                    key={flag.id}
                    tone={flagTone(flag)}
                    title={`${flag.company.nome} · ${flag.company.setor}`}
                    description={flag.descricao}
                    timestamp={formatDateTime(flag.updated_at)}
                  />
                ))}
              </div>
            )}
          </section>

          <section className="flex flex-col gap-2 rounded-xl border border-argos-100 bg-white p-5">
            <SectionHeader title="Últimos comunicados" />
            <EmptyState
              title="Sem comunicados"
              description="Este módulo ainda não foi implementado no Argos."
            />
          </section>
        </div>
      </div>

      <section className="flex flex-col gap-3 rounded-xl border border-argos-100 bg-white p-5">
        <SectionHeader
          title="Dados recentes de mercado"
          action={
            <Link href="/mercado" className="text-xs font-medium text-argos-600 underline">
              Ver mercado completo →
            </Link>
          }
        />
        {loading ? (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-20 animate-pulse rounded-lg bg-argos-50" />
            ))}
          </div>
        ) : !overview || overview.indicators.every((indicator) => indicator.value === null) ? (
          <EmptyState
            title="Ainda não há dados macro"
            description="Rode a coleta diária de mercado para popular Selic, IPCA e a curva de DI."
          />
        ) : (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {overview.indicators.map((indicator) => (
              <MetricCard
                key={indicator.key}
                label={indicator.label}
                value={indicator.value === null ? "—" : formatPercent(indicator.value)}
                caption={formatDate(indicator.reference_date)}
              />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
