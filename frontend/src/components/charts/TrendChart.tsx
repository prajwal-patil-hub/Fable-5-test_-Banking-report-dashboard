"use client";

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { KpiHistoryResponse } from "@/lib/api";
import { formatValue } from "@/lib/format";
import {
  AXIS_TICK,
  CHART_COLORS,
  CURSOR_STYLE,
  DOT_FILL,
  GRID_STROKE,
  TOOLTIP_LABEL_STYLE,
  TOOLTIP_STYLE,
} from "./theme";

/**
 * Multi-year trend for 2–3 KPIs of a module, merged on fiscal_year.
 * Thin gold/bronze lines with soft area fills — no gridline clutter.
 */
export function TrendChart({ series }: { series: KpiHistoryResponse[] }) {
  // Merge all series into rows keyed by fiscal year (ascending).
  const yearSet = new Set<string>();
  for (const s of series) for (const p of s.series) yearSet.add(p.fiscal_year);
  const years = [...yearSet].sort();
  const rows = years.map((fy) => {
    const row: Record<string, string | number | null> = { fiscal_year: fy };
    for (const s of series) {
      row[s.kpi_code] =
        s.series.find((p) => p.fiscal_year === fy)?.value ?? null;
    }
    return row;
  });

  const unit = series[0]?.unit ?? "percent";

  return (
    <div className="h-72 w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -16 }}>
          <defs>
            {series.map((s, i) => (
              <linearGradient
                key={s.kpi_code}
                id={`trend-${s.kpi_code}`}
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop
                  offset="0%"
                  stopColor={CHART_COLORS[i % CHART_COLORS.length]}
                  stopOpacity={0.22}
                />
                <stop
                  offset="100%"
                  stopColor={CHART_COLORS[i % CHART_COLORS.length]}
                  stopOpacity={0}
                />
              </linearGradient>
            ))}
          </defs>
          <CartesianGrid
            stroke={GRID_STROKE}
            strokeOpacity={0.55}
            vertical={false}
          />
          <XAxis
            dataKey="fiscal_year"
            tick={AXIS_TICK}
            axisLine={{ stroke: GRID_STROKE }}
            tickLine={false}
          />
          <YAxis
            tick={AXIS_TICK}
            axisLine={false}
            tickLine={false}
            width={64}
            domain={["auto", "auto"]}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={CURSOR_STYLE}
            formatter={(value: number | string, name: string) => {
              const s = series.find((x) => x.kpi_code === name);
              return [
                typeof value === "number"
                  ? formatValue(value, s?.unit ?? unit)
                  : "—",
                s?.name ?? name,
              ];
            }}
          />
          {series.map((s, i) => (
            <Area
              key={s.kpi_code}
              type="monotone"
              dataKey={s.kpi_code}
              stroke={CHART_COLORS[i % CHART_COLORS.length]}
              strokeWidth={1.5}
              fill={`url(#trend-${s.kpi_code})`}
              dot={{
                r: 2.5,
                fill: DOT_FILL,
                stroke: CHART_COLORS[i % CHART_COLORS.length],
                strokeWidth: 1,
              }}
              activeDot={{ r: 4 }}
              connectNulls
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
      {/* Legend */}
      <div className="mt-3 flex flex-wrap items-center gap-5">
        {series.map((s, i) => (
          <span
            key={s.kpi_code}
            className="flex items-center gap-2 text-[11px] uppercase tracking-[0.15em] text-text-secondary"
          >
            <span
              className="inline-block h-px w-5"
              style={{ background: CHART_COLORS[i % CHART_COLORS.length] }}
            />
            {s.name}
          </span>
        ))}
      </div>
    </div>
  );
}
