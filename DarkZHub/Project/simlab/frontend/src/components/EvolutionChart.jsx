import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

/**
 * Dual-axis trajectory chart: resistant-allele frequency (left, purple) and
 * surviving population (right, dashed grey), with a dashed 50% reference
 * line. `currentGen` draws a vertical marker kept in sync with the
 * EvolutionArena; clicking the chart reports the clicked generation.
 */
export default function EvolutionChart({
  generations,
  currentGen = null,
  onGenClick,
}) {
  return (
    <ResponsiveContainer width="100%" height={380}>
      <LineChart
        data={generations}
        margin={{ top: 5, right: 10, left: 0, bottom: 5 }}
        onClick={(state) => {
          const label = state?.activeLabel;
          if (label != null && onGenClick) onGenClick(Number(label));
        }}
      >
        <CartesianGrid stroke="#2b2440" strokeDasharray="3 3" />
        <XAxis dataKey="gen" stroke="#928aa6" tick={{ fontSize: 11 }} />
        <YAxis
          yAxisId="freq"
          domain={[0, 1]}
          stroke="#a78bfa"
          tick={{ fontSize: 11 }}
          width={44}
        />
        <YAxis
          yAxisId="pop"
          orientation="right"
          stroke="#928aa6"
          tick={{ fontSize: 11 }}
          width={56}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: "#161320",
            border: "1px solid #2b2440",
            borderRadius: 6,
          }}
          labelStyle={{ color: "#e8e4f3" }}
        />
        <Legend wrapperStyle={{ color: "#928aa6", fontSize: 12 }} />
        <ReferenceLine
          yAxisId="freq"
          y={0.5}
          stroke="#a78bfa"
          strokeDasharray="4 4"
          strokeOpacity={0.55}
          label={{ value: "50%", fill: "#928aa6", fontSize: 11, position: "insideTopRight" }}
        />
        {currentGen != null && (
          <ReferenceLine
            yAxisId="freq"
            x={currentGen}
            stroke="#e8e4f3"
            strokeOpacity={0.5}
            strokeDasharray="2 3"
          />
        )}
        <Line
          yAxisId="freq"
          dataKey="freq"
          name="Resistant frequency"
          stroke="#a78bfa"
          strokeWidth={2}
          dot={false}
        />
        <Line
          yAxisId="pop"
          dataKey="size"
          name="Population"
          stroke="#6f6787"
          strokeWidth={1.4}
          strokeDasharray="5 4"
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
