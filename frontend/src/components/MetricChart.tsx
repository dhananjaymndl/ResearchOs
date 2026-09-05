import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface Point {
  label: string;
  value: number | null;
  isBest?: boolean;
}

export default function MetricChart({ points, metricLabel }: { points: Point[]; metricLabel: string }) {
  const data = points
    .filter((p) => p.value != null)
    .map((p) => ({ name: p.label, value: p.value as number, isBest: p.isBest }));

  if (data.length === 0) return null;

  return (
    <ResponsiveContainer width="100%" height={180}>
      <LineChart data={data} margin={{ top: 8, right: 12, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e8eaed" vertical={false} />
        <XAxis
          dataKey="name"
          stroke="#5f6368"
          fontSize={11}
          tickLine={false}
          axisLine={{ stroke: "#dadce0" }}
        />
        <YAxis stroke="#5f6368" fontSize={11} tickLine={false} axisLine={false} width={44} />
        <Tooltip
          contentStyle={{
            background: "#ffffff",
            border: "1px solid #dadce0",
            borderRadius: 10,
            fontSize: 12,
            color: "#202124",
            boxShadow: "0 1px 3px 0 rgba(60,64,67,0.3), 0 4px 8px 3px rgba(60,64,67,0.15)",
          }}
          labelStyle={{ color: "#5f6368" }}
          formatter={(value: number) => [value.toFixed(4), metricLabel.toUpperCase()]}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#1a73e8"
          strokeWidth={2.5}
          dot={{ r: 4, fill: "#ffffff", stroke: "#1a73e8", strokeWidth: 2 }}
          activeDot={{ r: 6, fill: "#1a73e8" }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
