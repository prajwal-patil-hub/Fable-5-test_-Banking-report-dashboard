"use client";

import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { BenchmarkPeer, KpiUnit } from "@/lib/api";
import { formatValue } from "@/lib/format";
import {
  AXIS_TICK,
  BAR_PEER,
  BAR_SELECTED,
  GRID_STROKE,
  TOOLTIP_LABEL_STYLE,
  TOOLTIP_STYLE,
} from "./theme";

/**
 * Horizontal peer comparison — the selected institution's bar in gold,
 * peers in bronze.
 */
export function PeerBarChart({
  peers,
  selectedBankId,
  unit,
  height = 260,
}: {
  peers: BenchmarkPeer[];
  selectedBankId: number | null;
  unit: KpiUnit;
  height?: number;
}) {
  const data = [...peers].sort((a, b) => a.rank - b.rank);

  return (
    <div style={{ height }} className="w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 16, bottom: 4, left: 8 }}
          barCategoryGap="28%"
        >
          <XAxis type="number" hide domain={[0, "auto"]} />
          <YAxis
            type="category"
            dataKey="bank_code"
            tick={AXIS_TICK}
            width={64}
            axisLine={{ stroke: GRID_STROKE }}
            tickLine={false}
          />
          <Tooltip
            contentStyle={TOOLTIP_STYLE}
            labelStyle={TOOLTIP_LABEL_STYLE}
            cursor={{ fill: GRID_STROKE, fillOpacity: 0.35 }}
            formatter={(value: number | string) => [
              typeof value === "number" ? formatValue(value, unit) : "—",
              "Value",
            ]}
            labelFormatter={(label: string) => {
              const peer = data.find((p) => p.bank_code === label);
              return peer
                ? `${peer.bank_name} · Rank ${peer.rank}`
                : String(label);
            }}
          />
          <Bar dataKey="value" radius={0} maxBarSize={18} isAnimationActive={false}>
            {data.map((peer) => (
              <Cell
                key={peer.bank_id}
                fill={peer.bank_id === selectedBankId ? BAR_SELECTED : BAR_PEER}
                fillOpacity={peer.bank_id === selectedBankId ? 1 : 0.9}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
