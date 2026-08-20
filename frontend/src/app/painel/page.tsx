"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { fetchJson } from "@/lib/api";
import { fetchAllTrackedFlags, OPEN_FLAG_STATUSES } from "@/lib/creditAggregation";
import type { Company } from "@/types/credit";
import { CompanyForm } from "@/components/credit/CompanyForm";
import { DataTable, type DataTableColumn } from "@/components/ui/DataTable";
import { SectionHeader } from "@/components/ui/SectionHeader";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";

type CompanyRow = Company & { openFlags: number };

export default function PainelPage() {
  const router = useRouter();
  const [rows, setRows] = useState<CompanyRow[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);

  const load = () => {
    fetchJson<Company[]>("/api/companies")
      .then(async (companies) => {
        const flags = await fetchAllTrackedFlags(companies);
        const openByCompany = new Map<number, number>();
        flags.forEach((flag) => {
          if (OPEN_FLAG_STATUSES.has(flag.status)) {
            openByCompany.set(flag.company_id, (openByCompany.get(flag.company_id) ?? 0) + 1);
          }
        });
        setRows(companies.map((company) => ({ ...company, openFlags: openByCompany.get(company.id) ?? 0 })));
      })
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    load();
  }, []);

  const columns: DataTableColumn<CompanyRow>[] = [
    {
      key: "nome",
      header: "Empresa",
      render: (row) => <span className="font-medium text-argos-950">{row.nome}</span>,
    },
    { key: "setor", header: "Setor", render: (row) => row.setor },
    { key: "grupo", header: "Grupo econômico", render: (row) => row.grupo_economico ?? "—" },
    {
      key: "riscos",
      header: "Riscos em atenção",
      render: (row) =>
        row.openFlags > 0 ? (
          <StatusBadge tone="atencao">{row.openFlags}</StatusBadge>
        ) : (
          <StatusBadge tone="positivo">0</StatusBadge>
        ),
    },
    {
      key: "acao",
      header: "Ação",
      align: "right",
      render: () => <span className="text-xs font-medium text-argos-600">Ver detalhes →</span>,
    },
  ];

  return (
    <div className="flex w-full flex-col gap-6 px-8 py-6">
      <SectionHeader
        title="Empresas monitoradas"
        action={
          <button
            type="button"
            onClick={() => setShowForm((value) => !value)}
            className="rounded-full bg-argos-400 px-4 py-1.5 text-xs font-medium text-white transition hover:bg-argos-500"
          >
            {showForm ? "Cancelar" : "+ Nova empresa"}
          </button>
        }
      />

      {showForm && (
        <CompanyForm
          onCreated={() => {
            setShowForm(false);
            load();
          }}
        />
      )}

      {loading ? (
        <div className="h-60 animate-pulse rounded-xl bg-white/60" />
      ) : !rows || rows.length === 0 ? (
        <EmptyState title="Nenhuma empresa cadastrada" description="Cadastre a primeira empresa acima para começar a monitorar." />
      ) : (
        <DataTable
          columns={columns}
          rows={rows}
          rowKey={(row) => row.id}
          onRowClick={(row) => router.push(`/empresas/${row.id}`)}
        />
      )}
    </div>
  );
}
