import { fetchJson } from "./api";
import type { Company, TrackedFlag } from "@/types/credit";
import type { StatusTone } from "@/components/ui/StatusBadge";

export type FlagWithCompany = TrackedFlag & { company: Company };

export function flagTone(flag: Pick<TrackedFlag, "categoria" | "status">): StatusTone {
  if (flag.status === "revertido" || flag.status === "resolvido") return "positivo";
  if (flag.categoria === "red_flag") return flag.status === "confirmado" ? "critico" : "atencao";
  return flag.status === "confirmado" ? "atencao" : "observacao";
}

export const OPEN_FLAG_STATUSES = new Set(["aberto", "confirmado"]);

export function companyRiskStatus(flags: Pick<TrackedFlag, "categoria" | "status">[]): { tone: StatusTone; label: string } {
  const open = flags.filter((flag) => OPEN_FLAG_STATUSES.has(flag.status));
  const hasOpenRedFlag = open.some((flag) => flag.categoria === "red_flag");
  if (hasOpenRedFlag) return { tone: "critico", label: "Atenção" };
  if (open.length > 0) return { tone: "observacao", label: "Em observação" };
  return { tone: "positivo", label: "Estável" };
}

// Sem endpoint agregado no backend (deliberado - ver conversa de organização das
// APIs); para a primeira versão navegável, agregamos no cliente com uma
// chamada por empresa. Aceitável no volume atual de empresas cadastradas.
export async function fetchAllTrackedFlags(companies: Company[]): Promise<FlagWithCompany[]> {
  const perCompany = await Promise.all(
    companies.map((company) =>
      fetchJson<TrackedFlag[]>(`/api/companies/${company.id}/tracked-flags`)
        .then((flags) => flags.map((flag) => ({ ...flag, company })))
        .catch(() => [] as FlagWithCompany[])
    )
  );
  return perCompany.flat().sort((a, b) => (a.updated_at < b.updated_at ? 1 : -1));
}
