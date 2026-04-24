import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { analyzePortfolio } from "./api.js";

function mergeChartData(portfolio_curve = [], benchmark_curve = []) {
  const byDate = new Map();
  for (const p of portfolio_curve) {
    byDate.set(p.date, { date: p.date, portfolio: p.value });
  }
  for (const b of benchmark_curve) {
    const row = byDate.get(b.date) || { date: b.date };
    row.benchmark = b.value;
    byDate.set(b.date, row);
  }
  return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function fmtPct(x, decimals = 2) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return `${(Number(x) * 100).toFixed(decimals)}%`;
}

function fmtNum(x, decimals = 4) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return Number(x).toFixed(decimals);
}

function validateRows(rows) {
  const assets = rows
    .map((row) => ({
      ticker: String(row.ticker || "").trim().toUpperCase(),
      weight: parseFloat(row.weight),
    }))
    .filter((row) => row.ticker.length > 0);

  if (assets.length < 1) {
    return { ok: false, message: "Add at least one asset with a ticker." };
  }
  for (const a of assets) {
    if (Number.isNaN(a.weight) || a.weight <= 0) {
      return { ok: false, message: "Each asset must have a weight greater than 0." };
    }
  }
  return { ok: true, assets };
}

export default function App() {
  const [rows, setRows] = useState([{ ticker: "AAPL", weight: "1" }]);
  const [years, setYears] = useState(5);
  const [dividends, setDividends] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const chartData = useMemo(
    () => mergeChartData(result?.portfolio_curve, result?.benchmark_curve),
    [result]
  );

  const chartReady =
    chartData.length > 0 &&
    chartData.some((r) => typeof r.portfolio === "number" || typeof r.benchmark === "number");

  function updateRow(i, field, value) {
    setRows((r) => r.map((row, j) => (j === i ? { ...row, [field]: value } : row)));
  }

  function addRow() {
    setRows((r) => [...r, { ticker: "", weight: "" }]);
  }

  function removeRow(i) {
    setRows((r) => (r.length <= 1 ? r : r.filter((_, j) => j !== i)));
  }

  async function handleAnalyze() {
    setError(null);
    setResult(null);

    const check = validateRows(rows);
    if (!check.ok) {
      setError(check.message);
      return;
    }

    const body = {
      portfolio: check.assets,
      years: Number(years),
      dividends: Boolean(dividends),
    };

    setLoading(true);
    try {
      const data = await analyzePortfolio(body);
      setResult(data);
    } catch (e) {
      setError(e.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <h1>Portfolio Ranker</h1>

      <section>
        <h2>Portfolio</h2>
        <table>
          <thead>
            <tr>
              <th>Ticker</th>
              <th>Weight</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i}>
                <td>
                  <input
                    value={row.ticker}
                    onChange={(e) => updateRow(i, "ticker", e.target.value)}
                    placeholder="e.g. MSFT"
                  />
                </td>
                <td>
                  <input
                    type="number"
                    step="any"
                    min="0.0001"
                    value={row.weight}
                    onChange={(e) => updateRow(i, "weight", e.target.value)}
                  />
                </td>
                <td>
                  <button type="button" onClick={() => removeRow(i)} disabled={rows.length <= 1}>
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button" onClick={addRow}>
          Add asset
        </button>

        <label>
          Years
          <select value={years} onChange={(e) => setYears(Number(e.target.value))}>
            <option value={5}>5</option>
            <option value={10}>10</option>
          </select>
        </label>

        <label>
          <input
            type="checkbox"
            checked={dividends}
            onChange={(e) => setDividends(e.target.checked)}
          />{" "}
          Include dividends (flag for backend)
        </label>

        <div>
          <button type="button" onClick={handleAnalyze} disabled={loading}>
            {loading ? "Loading..." : "Analyze Portfolio"}
          </button>
        </div>
      </section>

      {error ? <p className="error">{error}</p> : null}

      {result ? (
        <section>
          <h2>Results</h2>
          <ul>
            <li>Score: {fmtNum(result.score, 2)}</li>
            <li>Rank: {result.rank}</li>
            <li>Annual return: {fmtPct(result.annual_return, 2)}</li>
            <li>Volatility (ann.): {fmtPct(result.volatility, 2)}</li>
            <li>Max drawdown: {fmtPct(result.drawdown, 2)}</li>
            <li>Sharpe (daily): {fmtNum(result.sharpe, 4)}</li>
          </ul>

          {chartReady ? (
            <>
              <h3>Portfolio vs benchmark</h3>
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tick={{ fontSize: 10 }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10 }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="portfolio" name="Portfolio" stroke="#2563eb" dot={false} />
                    <Line type="monotone" dataKey="benchmark" name="Benchmark" stroke="#16a34a" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <p>No chart data available.</p>
          )}
        </section>
      ) : null}
    </div>
  );
}
