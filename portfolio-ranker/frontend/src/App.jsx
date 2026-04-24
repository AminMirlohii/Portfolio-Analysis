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

function mergeChartData(curves) {
  const byDate = new Map();
  for (const [key, list] of Object.entries(curves)) {
    for (const point of list || []) {
      const row = byDate.get(point.date) || { date: point.date };
      row[key] = point.value;
      byDate.set(point.date, row);
    }
  }
  return Array.from(byDate.values()).sort((a, b) => a.date.localeCompare(b.date));
}

function filterByYears(data, years) {
  if (!Array.isArray(data) || data.length === 0) return [];
  const end = new Date(data[data.length - 1].date);
  const cutoff = new Date(end);
  cutoff.setFullYear(cutoff.getFullYear() - years);
  return data.filter((row) => new Date(row.date) >= cutoff);
}

function pctChangeFromCurve(curve) {
  if (!Array.isArray(curve) || curve.length < 2) return null;
  const first = Number(curve[0].value);
  const last = Number(curve[curve.length - 1].value);
  if (!Number.isFinite(first) || !Number.isFinite(last) || first <= 0) return null;
  return last / first - 1;
}

function mockIndexCurve(baseCurve, factor) {
  if (!Array.isArray(baseCurve) || baseCurve.length < 2) return [];
  const out = [{ date: baseCurve[0].date, value: 10000 }];
  for (let i = 1; i < baseCurve.length; i += 1) {
    const prev = Number(baseCurve[i - 1].value);
    const curr = Number(baseCurve[i].value);
    if (!Number.isFinite(prev) || !Number.isFinite(curr) || prev <= 0) {
      out.push({ date: baseCurve[i].date, value: out[out.length - 1].value });
      continue;
    }
    const r = curr / prev - 1;
    out.push({ date: baseCurve[i].date, value: out[out.length - 1].value * (1 + r * factor) });
  }
  return out;
}

function fmtPct(x, decimals = 2) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return `${(Number(x) * 100).toFixed(decimals)}%`;
}

function fmtNum(x, decimals = 4) {
  if (x == null || Number.isNaN(Number(x))) return "—";
  return Number(x).toFixed(decimals);
}

function modeLabel(mode) {
  if (mode === "dollar") return "Amount (USD)";
  return "Allocation units";
}

function buildPortfolioInput(rows, mode, totalValue) {
  const assets = rows
    .map((row) => ({
      ticker: String(row.ticker || "").trim().toUpperCase(),
      value: parseFloat(row.value),
    }))
    .filter((row) => row.ticker.length > 0);

  if (assets.length < 1) {
    return { ok: false, message: "Add at least one asset with a ticker." };
  }

  for (const a of assets) {
    if (Number.isNaN(a.value)) return { ok: false, message: "All allocations must be numeric." };
    if (a.value < 0) return { ok: false, message: "Allocations cannot be negative." };
  }

  const positives = assets.filter((a) => a.value > 0);
  if (positives.length < 1) {
    return { ok: false, message: "At least one asset must have value greater than 0." };
  }

  const sum = positives.reduce((acc, a) => acc + a.value, 0);
  if (sum <= 0) return { ok: false, message: "Total allocation must be greater than 0." };

  const portfolio = positives.map((a) => ({ ticker: a.ticker, weight: a.value / sum }));

  if (mode !== "total") {
    return { ok: true, portfolio, implied: [] };
  }

  const total = parseFloat(totalValue);
  if (Number.isNaN(total) || total <= 0) {
    return { ok: false, message: "Total portfolio value must be greater than 0 in total value mode." };
  }

  const implied = portfolio.map((a) => ({
    ticker: a.ticker,
    weight: a.weight,
    amount: a.weight * total,
  }));

  return { ok: true, portfolio, implied };
}

export default function App() {
  const [rows, setRows] = useState([{ ticker: "AAPL", value: "100" }]);
  const [inputMode, setInputMode] = useState("percentage");
  const [totalValue, setTotalValue] = useState("10000");
  const [impliedAllocations, setImpliedAllocations] = useState([]);
  const [rangeYears, setRangeYears] = useState(5);
  const [years, setYears] = useState(5);
  const [dividends, setDividends] = useState(true);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const portfolioCurve = result?.portfolio_curve || [];
  const spyCurve = result?.benchmark_curve || [];
  const qqqCurve = useMemo(() => mockIndexCurve(spyCurve, 1.25), [spyCurve]);
  const diaCurve = useMemo(() => mockIndexCurve(spyCurve, 0.85), [spyCurve]);

  const filteredPortfolio = useMemo(() => filterByYears(portfolioCurve, rangeYears), [portfolioCurve, rangeYears]);
  const filteredSpy = useMemo(() => filterByYears(spyCurve, rangeYears), [spyCurve, rangeYears]);
  const filteredQqq = useMemo(() => filterByYears(qqqCurve, rangeYears), [qqqCurve, rangeYears]);
  const filteredDia = useMemo(() => filterByYears(diaCurve, rangeYears), [diaCurve, rangeYears]);

  const chartData = useMemo(
    () =>
      mergeChartData({
        portfolio: filteredPortfolio,
        spy: filteredSpy,
        qqq: filteredQqq,
        dia: filteredDia,
      }),
    [filteredPortfolio, filteredSpy, filteredQqq, filteredDia]
  );

  const chartReady =
    chartData.length > 0 &&
    chartData.some(
      (r) =>
        typeof r.portfolio === "number" ||
        typeof r.spy === "number" ||
        typeof r.qqq === "number" ||
        typeof r.dia === "number"
    );

  const portfolioChange = pctChangeFromCurve(filteredPortfolio);
  const spyChange = pctChangeFromCurve(filteredSpy);
  const volatility = result?.volatility ?? null;
  const drawdown = result?.drawdown ?? null;
  const sharpe = result?.sharpe ?? null;

  const marketInterpretation =
    portfolioChange != null && spyChange != null
      ? portfolioChange >= spyChange
        ? "Outperforms S&P 500"
        : "Underperforms market"
      : "Run an analysis to compare against market";

  const volatilityInterpretation =
    volatility == null ? "Run analysis to assess volatility" : volatility >= 0.25 ? "High volatility portfolio" : "Stable portfolio";

  const riskScore =
    volatility == null || drawdown == null
      ? null
      : Math.min(1, Math.max(0, volatility / 0.35)) * 0.6 + Math.min(1, Math.max(0, drawdown / 0.4)) * 0.4;
  const riskLevel = riskScore == null ? "N/A" : riskScore < 0.33 ? "Low" : riskScore < 0.66 ? "Medium" : "High";
  const riskPct = riskScore == null ? 0 : Math.round(riskScore * 100);

  function updateRow(i, field, value) {
    setRows((r) => r.map((row, j) => (j === i ? { ...row, [field]: value } : row)));
  }

  function addRow() {
    setRows((r) => [...r, { ticker: "", value: "" }]);
  }

  function removeRow(i) {
    setRows((r) => (r.length <= 1 ? r : r.filter((_, j) => j !== i)));
  }

  async function handleAnalyze() {
    setError(null);
    setResult(null);
    setImpliedAllocations([]);

    const check = buildPortfolioInput(rows, inputMode, totalValue);
    if (!check.ok) {
      setError(check.message);
      return;
    }

    setImpliedAllocations(check.implied || []);

    const body = {
      portfolio: check.portfolio,
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
    <div className="app">
      <header className="app-header">
        <h1>Portfolio Ranker</h1>
        <p>Build a weighted portfolio and compare it against SPY.</p>
      </header>

      <main className="dashboard">
        <section className="card input-panel">
          <h2>Portfolio Input</h2>

          <div className="mode-toggle">
            <button
              type="button"
              className={inputMode === "percentage" ? "ghost-btn active" : "ghost-btn"}
              onClick={() => setInputMode("percentage")}
            >
              Percentage mode
            </button>
            <button
              type="button"
              className={inputMode === "dollar" ? "ghost-btn active" : "ghost-btn"}
              onClick={() => setInputMode("dollar")}
            >
              Dollar amount mode
            </button>
            <button
              type="button"
              className={inputMode === "total" ? "ghost-btn active" : "ghost-btn"}
              onClick={() => setInputMode("total")}
            >
              Total portfolio value mode
            </button>
          </div>

          {inputMode === "total" ? (
            <label>
              Total Portfolio Value (USD)
              <input
                type="number"
                min="0.01"
                step="any"
                value={totalValue}
                onChange={(e) => setTotalValue(e.target.value)}
              />
            </label>
          ) : null}

          <table className="asset-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>{modeLabel(inputMode)}</th>
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
                      min="0"
                      value={row.value}
                      onChange={(e) => updateRow(i, "value", e.target.value)}
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

          <div className="row-actions">
            <button type="button" className="ghost-btn" onClick={addRow}>
              Add Asset
            </button>
          </div>

          <label>
            Analysis Horizon (backend)
            <select value={years} onChange={(e) => setYears(Number(e.target.value))}>
              <option value={5}>5</option>
              <option value={10}>10</option>
            </select>
          </label>

          <label>
            Chart Time Range
            <select value={rangeYears} onChange={(e) => setRangeYears(Number(e.target.value))}>
              <option value={1}>1 year</option>
              <option value={5}>5 years</option>
              <option value={10}>10 years</option>
            </select>
          </label>

          <label className="checkbox">
            <input
              type="checkbox"
              checked={dividends}
              onChange={(e) => setDividends(e.target.checked)}
            />
            <span>Include dividends</span>
          </label>

          <button type="button" className="primary-btn" onClick={handleAnalyze} disabled={loading}>
            {loading ? "Loading..." : "Analyze Portfolio"}
          </button>

          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="results-panel">
          <div className="card">
            <h2>Portfolio Performance</h2>
            {result ? (
              <div className="metrics-grid">
                <div className="metric-item">
                  <span>Score</span>
                  <strong>{fmtNum(result.score, 2)}</strong>
                </div>
                <div className="metric-item">
                  <span>Rank</span>
                  <strong>{result.rank}</strong>
                </div>
              </div>
            ) : (
              <p className="empty">Run an analysis to see performance.</p>
            )}
          </div>

          <div className="card analytics-card">
            <h2>Advanced Analytics</h2>
            <div className="analytics-grid">
              <div className="analytic-pill">
                <span>Total Return</span>
                <strong>{fmtPct(portfolioChange, 2)}</strong>
              </div>
              <div className="analytic-pill">
                <span>Volatility</span>
                <strong>{fmtPct(volatility, 2)}</strong>
              </div>
              <div className="analytic-pill">
                <span>Max Drawdown</span>
                <strong>{fmtPct(drawdown, 2)}</strong>
              </div>
              <div className="analytic-pill">
                <span>Sharpe Ratio</span>
                <strong>{fmtNum(sharpe, 4)}</strong>
              </div>
            </div>

            <div className="interpretation">
              <p>{marketInterpretation}</p>
              <p>{volatilityInterpretation}</p>
            </div>

            <div className="risk-meter">
              <div className="risk-header">
                <span>Risk Meter</span>
                <strong>{riskLevel}</strong>
              </div>
              <div className="risk-track">
                <div className="risk-fill" style={{ width: `${riskPct}%` }} />
              </div>
              <small>{riskLevel === "N/A" ? "Need volatility and drawdown data" : `${riskPct}% risk intensity`}</small>
            </div>
          </div>

          <div className="card">
            <h2>Metrics Summary</h2>
            {result ? (
              <ul className="metrics-list">
                <li>Annual return: {fmtPct(result.annual_return, 2)}</li>
                <li>Volatility (ann.): {fmtPct(result.volatility, 2)}</li>
                <li>Max drawdown: {fmtPct(result.drawdown, 2)}</li>
                <li>Sharpe (daily): {fmtNum(result.sharpe, 4)}</li>
              </ul>
            ) : (
              <p className="empty">Metrics will appear here.</p>
            )}
          </div>

          <div className="card">
            <h2>Index Comparison ({rangeYears}Y)</h2>
            <div className="metrics-list">
              <div>Portfolio: {fmtPct(pctChangeFromCurve(filteredPortfolio), 2)}</div>
              <div>S&P 500 (SPY): {fmtPct(pctChangeFromCurve(filteredSpy), 2)}</div>
              <div>Nasdaq (QQQ): {fmtPct(pctChangeFromCurve(filteredQqq), 2)}</div>
              <div>Dow Jones (DIA): {fmtPct(pctChangeFromCurve(filteredDia), 2)}</div>
            </div>
            {inputMode === "total" && impliedAllocations.length > 0 ? (
              <div className="implied-block">
                <h3>Implied Allocations (USD)</h3>
                <ul className="metrics-list">
                  {impliedAllocations.map((a) => (
                    <li key={a.ticker}>
                      {a.ticker}: ${fmtNum(a.amount, 2)} ({fmtPct(a.weight, 2)})
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </div>

          <div className="card chart-card">
            <h2>Charts Area</h2>
            {chartReady ? (
              <div style={{ width: "100%", height: 340 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData} margin={{ top: 8, right: 8, left: 8, bottom: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#2a2f3a" />
                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#9ca3af" }} interval="preserveStartEnd" />
                    <YAxis tick={{ fontSize: 10, fill: "#9ca3af" }} />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="portfolio" name="Portfolio" stroke="#3b82f6" dot={false} />
                    <Line type="monotone" dataKey="spy" name="SPY" stroke="#22c55e" dot={false} />
                    <Line type="monotone" dataKey="qqq" name="QQQ" stroke="#f59e0b" dot={false} />
                    <Line type="monotone" dataKey="dia" name="DIA" stroke="#ef4444" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <p className="empty">No chart data available yet.</p>
            )}
          </div>

          <div className="card chart-card">
            <h2>AI Analysis</h2>
            <p className="empty">
              This section will provide narrative insights, portfolio diagnostics, and actionable improvement suggestions.
            </p>
          </div>
        </section>
      </main>
    </div>
  );
}
