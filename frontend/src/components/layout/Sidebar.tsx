"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

type NavItem = {
  href: string;
  label: string;
  icon: ReactNode;
  isActive: (pathname: string) => boolean;
};

const ICON_PROPS = { width: 18, height: 18, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor", strokeWidth: 1.75 };

const NAV_ITEMS: NavItem[] = [
  {
    href: "/",
    label: "Inicial",
    isActive: (pathname) => pathname === "/",
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M3 10.5 12 3l9 7.5" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M5 9.5V20a1 1 0 0 0 1 1h4v-6h4v6h4a1 1 0 0 0 1-1V9.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: "/painel",
    label: "Painel",
    isActive: (pathname) => pathname === "/painel" || pathname.startsWith("/empresas"),
    icon: (
      <svg {...ICON_PROPS}>
        <rect x="3.5" y="3.5" width="7" height="7" rx="1.2" />
        <rect x="13.5" y="3.5" width="7" height="7" rx="1.2" />
        <rect x="3.5" y="13.5" width="7" height="7" rx="1.2" />
        <rect x="13.5" y="13.5" width="7" height="7" rx="1.2" />
      </svg>
    ),
  },
  {
    href: "/mercado",
    label: "Mercado",
    isActive: (pathname) => pathname.startsWith("/mercado"),
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M4 19V9M10 19V5M16 19v-7M22 19V3" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
  {
    href: "/resultados",
    label: "Resultados",
    isActive: (pathname) => pathname.startsWith("/resultados"),
    icon: (
      <svg {...ICON_PROPS}>
        <path d="M6 3h9l5 5v13a1 1 0 0 1-1 1H6a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1Z" strokeLinejoin="round" />
        <path d="M9 13h6M9 17h6M9 9h2" strokeLinecap="round" />
      </svg>
    ),
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-full w-60 shrink-0 flex-col bg-argos-950 text-white">
      <div className="px-5 pt-6 pb-5">
        <Link href="/" className="text-lg font-semibold tracking-[0.15em]">
          ARGOS
        </Link>
      </div>

      <nav className="flex flex-col gap-1 px-3">
        {NAV_ITEMS.map((item) => {
          const active = item.isActive(pathname);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition ${
                active ? "bg-argos-400 text-argos-950" : "text-argos-100/80 hover:bg-white/5 hover:text-white"
              }`}
            >
              {item.icon}
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto flex flex-col gap-1 border-t border-white/10 px-5 py-4 text-xs text-argos-100/70">
        <button
          type="button"
          className="flex items-center justify-between text-left font-medium text-white/90 hover:text-white"
        >
          EQI Produtos
          <span aria-hidden>▾</span>
        </button>
        <p>Domínio de crédito · Argos</p>
      </div>
    </aside>
  );
}
