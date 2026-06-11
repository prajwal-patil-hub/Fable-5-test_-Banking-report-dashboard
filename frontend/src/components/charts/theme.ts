/** Shared Recharts styling for the Sovereign dark/gold theme. */

export const CHART_COLORS = ["#C7A56A", "#9C7B4F", "#D8C49A"];

export const AXIS_TICK = {
  fill: "#CFC3B0",
  fontSize: 11,
  fontFamily: "var(--font-sans)",
} as const;

export const TOOLTIP_STYLE: React.CSSProperties = {
  backgroundColor: "#2C1E16",
  border: "1px solid #4B382F",
  borderRadius: 0,
  fontSize: 12,
  color: "#F3EEE7",
  padding: "8px 12px",
};

export const TOOLTIP_LABEL_STYLE: React.CSSProperties = {
  color: "#C7A56A",
  textTransform: "uppercase",
  letterSpacing: "0.15em",
  fontSize: 10,
  marginBottom: 4,
};

export const CURSOR_STYLE = { stroke: "#4B382F", strokeWidth: 1 };
