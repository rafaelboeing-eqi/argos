"use client";

import { useEffect, useState } from "react";

import { fetchJson } from "@/lib/api";
import type { MarketOverview } from "@/types/market";
import { CommodityCard } from "@/components/market/CommodityCard";
import { CommodityHistoryPanel } from "@/components/market/CommodityHistoryPanel";
import { EmptyState } from "@/components/market/EmptyState";
import { IndicatorCard } from "@/components/market/IndicatorCard";
import { RateCurveChart } from "@/components/market/RateCurveChart";

export default function MercadoPage() {
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedCommodity, setSelectedCommodity] = useState<{ symbol: string; label: string } | null>(null);

  useEffect(() => {
    fetchJson<MarketOverview>("/api/market/overview")
      .then(setOverview)
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, []);

  const hasAnyIndicator = overview?.indicators.some((indicator) => indicator.value !== null) ?? false;

  return (
    <div className="mx-auto flex w-full max-w-6xl flex-col gap-8 px-6 py-10">
      <header className="flex flex-col gap-1">
        <h1 className="text-2xl font-semibold text-argos-950">Mercado</h1>
        <p className="text-sm text-argos-600">Panorama de juros, macro e commodities monitorados pelo Argos.</p>
      </header>

      <section className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
        {loading ? (
          Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="h-28 animate-pulse rounded-2xl bg-white/60" />
          ))
        ) : !overview || !hasAnyIndicator ? (
          <div className="col-span-full">
            <EmptyState
              title="Ainda não há dados macro"
              description="Rode a coleta diária (collect_daily_market_data) para popular Selic, IPCA e a curva de DI."
            />
          </div>
        ) : (
          overview.indicators.map((indicator) => <IndicatorCard key={indicator.key} indicator={indicator} />)
        )}
      </section>

      <RateCurveChart />

      <section className="flex flex-col gap-4">
        <h2 className="text-base font-semibold text-argos-950">Commodities</h2>
        {loading ? (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, index) => (
              <div key={index} className="h-40 animate-pulse rounded-2xl bg-white/60" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            {overview?.commodities.map((commodity) => (
              <CommodityCard
                key={commodity.asset}
                commodity={commodity}
                onClick={() =>
                  commodity.symbol && setSelectedCommodity({ symbol: commodity.symbol, label: commodity.label })
                }
              />
            ))}
          </div>
        )}
      </section>

      {selectedCommodity && (
        <CommodityHistoryPanel
          key={selectedCommodity.symbol}
          symbol={selectedCommodity.symbol}
          label={selectedCommodity.label}
          onClose={() => setSelectedCommodity(null)}
        />
      )}
    </div>
  );
}
