/** Shared Recharts styling — "Old Money Daylight, minimal" theme. */

export const CHART_COLORS = ["#8C6D3F", "#A6957C", "#C9B48C"];

/** Axis/grid hairlines and neutral fills on near-white surfaces. */
export const GRID_STROKE = "#E6DFCE";
export const DOT_FILL = "#FFFFFF";
/** Peer bars: selected institution in the accent gold, peers muted sand. */
export const BAR_SELECTED = "#8C6D3F";
export const BAR_PEER = "#DAD1BC";

export const AXIS_TICK = {
  fill: "#7A7060",
  fontSize: 11,
  fontFamily: "var(--font-sans)",
} as const;

export const TOOLTIP_STYLE: React.CSSProperties = {
  backgroundColor: "#FFFFFF",
  border: "1px solid #E6DFCE",
  borderRadius: 0,
  fontSize: 12,
  color: "#26221A",
  padding: "8px 12px",
  boxShadow: "0 2px 10px rgba(38, 34, 26, 0.07)",
};

export const TOOLTIP_LABEL_STYLE: React.CSSProperties = {
  color: "#8C6D3F",
  textTransform: "uppercase",
  letterSpacing: "0.15em",
  fontSize: 10,
  marginBottom: 4,
};

export const CURSOR_STYLE = { stroke: "#E6DFCE", strokeWidth: 1 };
