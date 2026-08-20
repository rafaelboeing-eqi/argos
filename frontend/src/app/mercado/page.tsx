"use client";

import { useEffect, useState } from "react";

import { fetchJson } from "@/lib/api";
import type { MarketOverview } from "@/types/market";
import { CommodityCard } from "@/components/market/CommodityCard";
import { CommodityHistoryChart } from "@/components/market/CommodityHistoryChart";
import { DataFreshnessBadge } from "@/components/market/DataFreshnessBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { IndicatorCard } from "@/components/market/IndicatorCard";
import { RateCurveChart } from "@/components/market/RateCurveChart";
import { TreasuryCurveChart } from "@/components/market/TreasuryCurveChart";

export default function MercadoPage() {
  const [overview, setOverview] = useState<MarketOverview | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchJson<MarketOverview>("/api/market/overview")
      .then(setOverview)
      .catch(() => setOverview(null))
      .finally(() => setLoading(false));
  }, []);

  const hasAnyIndicator = overview?.indicators.some((indicator) => indicator.value !== null) ?? false;

  return (
    <div className="flex w-full flex-col gap-6 px-8 py-6">
      {!loading && (
        <div className="flex justify-end">
          <DataFreshnessBadge dataAsOf={overview?.data_as_of ?? null} />
        </div>
      )}

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

      <TreasuryCurveChart />

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
            {overview?.commodities.map((commodity) => <CommodityCard key={commodity.asset} commodity={commodity} />)}
          </div>
        )}
      </section>

      {!loading && <CommodityHistoryChart commodities={overview?.commodities ?? []} />}
    </div>
  );
}
