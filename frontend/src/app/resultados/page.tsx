"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchJson } from "@/lib/api";
import { OPEN_FLAG_STATUSES } from "@/lib/creditAggregation";
import { formatCurrencyCompact, formatMultiple, formatRatioAsPercent } from "@/lib/format";
import type { Company, CreditMetric, TrackedFlag } from "@/types/credit";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";

type ResultRow = {
  company: Company;
  latest: CreditMetric | null;
  openFlags: number;
};

export default function ResultadosPage() {
  const router = useRouter();
  const [rows, setRows] = useState<ResultRow[] | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    fetchJson<Company[]>("/api/companies")
      .then(async (companies) => {
        const results = await Promise.all(
          companies.map(async (company) => {
            const [metrics, flags] = await Promise.all([
              fetchJson<CreditMetric[]>(`/api/companies/${company.id}/credit-metrics`).catch(() => [] as CreditMetric[]),
              fetchJson<TrackedFlag[]>(`/api/companies/${company.id}/tracked-flags`).catch(() => [] as TrackedFlag[]),
            ]);
            return {
              company,
              latest: metrics.length > 0 ? metrics[metrics.length - 1] : null,
              openFlags: flags.filter((flag) => OPEN_FLAG_STATUSES.has(flag.status)).length,
            } satisfies ResultRow;
          })
        );
        if (!cancelled) setRows(results);
      })
      .catch(() => {
        if (!cancelled) setRows([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const columns: DataTableColumn<ResultRow>[] = [
    {
      key: "empresa",
      header: "Empresa",
      render: (row) => (
        <div className="flex flex-col">
          <span className="font-medium text-argos-950">{row.company.nome}</span>
          <span className="text-xs text-argos-500">{row.company.setor}</span>
        </div>
      ),
    },
    { key: "periodo", header: "Último período", render: (row) => row.latest?.period ?? "—" },
    { key: "receita", header: "Receita líquida", align: "right", render: (row) => formatCurrencyCompact(row.latest?.receita_liquida ?? null) },
    { key: "ebitda", header: "EBITDA", align: "right", render: (row) => formatCurrencyCompact(row.latest?.ebitda ?? null) },
    { key: "margem", header: "Margem EBITDA", align: "right", render: (row) => formatRatioAsPercent(row.latest?.margem_ebitda ?? null) },
    { key: "leverage", header: "Dívida líq. / EBITDA", align: "right", render: (row) => formatMultiple(row.latest?.divida_liquida_ebitda ?? null) },
    {
      key: "flags",
      header: "Alertas disparados",
      align: "right",
      render: (row) =>
        row.openFlags > 0 ? <StatusBadge tone="atencao">{row.openFlags}</StatusBadge> : <StatusBadge tone="positivo">0</StatusBadge>,
    },
  ];

  return (
    <div className="flex w-full flex-col gap-6 px-8 py-6">
      <SectionHeader title="Resultados financeiros por empresa" />

      {loading ? (
        <div className="h-60 animate-pulse rounded-xl bg-white/60" />
      ) : !rows || rows.length === 0 ? (
        <EmptyState
          title="Nenhum resultado disponível"
          description="Cadastre empresas e ingira períodos financeiros no Painel para ver os resultados aqui."
        />
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.company.id}
          onRowClick={(row) => router.push(`/empresas/${row.company.id}`)}
        />
      )}
    </div>
  );
}
