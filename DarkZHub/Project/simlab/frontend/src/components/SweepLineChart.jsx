import {
  CartesianGrid,
  ErrorBar,
  Line,
  LineChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatTick, METRICS } from "./sweepMetrics.js";

/**
 * 1D sweep rendering: mean +/- std as a line with error bars.
 * Fixed canvas size so the chart is deterministic in tests; the wrapper
 * scrolls on narrow screens.
 */
export default function SweepLineChart({ axes, cells, metricKey }) {
  const metric = METRICS[metricKey];

  const data = [...(cells ?? [])]
    .sort((a, b) => a.a_index - b.a_index)
    .map((cell) => {
      const mean = metric.pick(cell);
      const std = metric.std(cell) ?? 0;
      return { x: cell.a, mean, err: [std, std] };
    });

  return (
    <div className="overflow-x-auto">
      <LineChart width={640} height={320} data={data} margin={{ top: 10, right: 20, bottom: 30, left: 10 }}>
        <CartesianGrid stroke="#2b2440" strokeDasharray="3 3" />
        <XAxis
          dataKey="x"
          type="category"
          stroke="#928aa6"
          tick={{ fontSize: 11 }}
          tickFormatter={formatTick}
          label={{
            value: axes.param_a,
            position: "insideBottom",
            offset: -20,
            fill: "#928aa6",
            fontSize: 11,
          }}
        />
        <YAxis stroke="#a78bfa" tick={{ fontSize: 11 }} width={48} />
        <Tooltip
          contentStyle={{
            backgroundColor: "#161320",
            border: "1px solid #2b2440",
            borderRadius: 6,
          }}
          labelStyle={{ color: "#e8e4f3" }}
          formatter={(value, name) =>
            Array.isArray(value) ? [`±${value[0]}`, name] : [value, name]
          }
        />
        <Line
          dataKey="mean"
          name={metric.label}
          stroke="#a78bfa"
          strokeWidth={2}
          dot={{ r: 3 }}
          isAnimationActive={false}
        >
          {/* ErrorBar must be a child of the Line it decorates. */}
          <ErrorBar dataKey="err" width={5} strokeWidth={1.5} stroke="#928aa6" direction="y" />
        </Line>
      </LineChart>
    </div>
  );
}
