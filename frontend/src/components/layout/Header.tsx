"use client";

import { usePathname } from "next/navigation";

const SECTION_TITLES: Array<{ prefix: string; title: string; subtitle: string }> = [
  { prefix: "/painel", title: "Painel", subtitle: "Empresas e ativos monitorados pelo Argos" },
  { prefix: "/empresas", title: "Empresa", subtitle: "Visão individual de crédito" },
  { prefix: "/mercado", title: "Mercado", subtitle: "Juros, macro e commodities monitorados" },
  { prefix: "/resultados", title: "Resultados", subtitle: "Resultados financeiros divulgados" },
];

function resolveSection(pathname: string) {
  if (pathname === "/") return { title: "Inicial", subtitle: "Visão geral do Argos" };
  return (
    SECTION_TITLES.find((section) => pathname.startsWith(section.prefix)) ?? {
      title: "Argos",
      subtitle: "",
    }
  );
}

export function Header() {
  const pathname = usePathname();
  const section = resolveSection(pathname);

  return (
    <header className="flex items-center justify-between gap-6 border-b border-argos-100 bg-white px-8 py-4">
      <div className="flex flex-col">
        <h1 className="text-lg font-semibold text-argos-950">{section.title}</h1>
        {section.subtitle && <p className="text-sm text-argos-600">{section.subtitle}</p>}
      </div>

      <div className="flex flex-1 items-center justify-end gap-4">
        <div className="relative hidden w-full max-w-sm sm:block">
          <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-argos-400">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3.5-3.5" strokeLinecap="round" />
            </svg>
          </span>
          <input
            type="text"
            placeholder="Buscar ativo, emissor ou setor"
            disabled
            className="w-full rounded-full border border-argos-100 bg-argos-50/60 py-2 pl-9 pr-3 text-sm text-argos-600 placeholder:text-argos-400 disabled:cursor-not-allowed"
          />
        </div>

        <button
          type="button"
          disabled
          className="flex h-9 w-9 items-center justify-center rounded-full border border-argos-100 text-argos-500 disabled:cursor-not-allowed"
          aria-label="Notificações"
        >
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75">
            <path d="M15 17H5l1.4-1.8A2 2 0 0 0 7 14V10a5 5 0 0 1 10 0v4c0 .4.1.8.4 1.1L19 17h-4" strokeLinecap="round" strokeLinejoin="round" />
            <path d="M10 19a2 2 0 0 0 4 0" strokeLinecap="round" />
          </svg>
        </button>

        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-argos-950 text-sm font-medium text-white">
          A
        </div>
      </div>
    </header>
  );
}
