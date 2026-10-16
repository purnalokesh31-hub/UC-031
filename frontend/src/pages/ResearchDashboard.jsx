import { useEffect, useState } from "react";
import { api } from "../api";
import { useWorkspace } from "../lib/WorkspaceStore";

const label = text => text.replaceAll("_", " ");
export default function ResearchDashboard() {
  const { store, update } = useWorkspace();
  const [metricsError, setMetricsError] = useState("");
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  const [runId, setRunId] = useState("primary");
  const [modelIndex, setModelIndex] = useState(0);
  const [dimension, setDimension] = useState("district");
  const [crop, setCrop] = useState("Rice");
  useEffect(() => {
    const controller = new AbortController();
    setMetricsError("");
    api.get("/metrics", { signal: controller.signal }).then(response => {
      if (response.data.error) throw new Error(response.data.error);
      update(() => ({ metrics: response.data }));
    }).catch(() => {
      if (!controller.signal.aborted) setMetricsError("Live metrics unavailable. Any displayed metrics are the last saved snapshot.");
    });
    return () => controller.abort();
  }, [retry, update]);
  useEffect(() => {
    const controller = new AbortController(); setError("");
    api.get("/research/evidence", { signal: controller.signal, timeout: 15000 }).then(r => setData(r.data)).catch(() => { if (!controller.signal.aborted) setError("Research reports could not be loaded. Start the backend and retry."); });
    return () => controller.abort();
  }, [retry]);
  const run = data?.runs.find(r => r.id === runId);
  const model = run?.models?.[modelIndex];
  const synthetic = store.metrics?.[crop];
  return <main className="page-content notebook-page"><header className="feature-page-heading"><p className="dashboard-eyebrow">MODEL EVIDENCE</p><h1>Performance, with the full context.</h1><p>Regression errors, uncertainty and generalization results. R² is not percentage accuracy, and interval coverage must be read alongside interval width.</p></header>
    <section className="feature-card"><h2>Deployed application · synthetic data</h2>{metricsError && <p role="status">{metricsError} <button className="btn-ghost" onClick={() => setRetry(n => n+1)}>Retry</button></p>}<label>Crop<select value={crop} onChange={e => setCrop(e.target.value)}>{["Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Groundnut"].map(c => <option key={c}>{c}</option>)}</select></label>{synthetic ? <div className="feature-table-scroll"><table><thead><tr><th>Family</th><th>MAE q/ha</th><th>RMSE q/ha</th><th>R²</th><th>90% coverage</th></tr></thead><tbody>{["classical", "quantum"].map(f => <tr key={f}><th>{f === "classical" ? "Classical" : "Quantum simulation"}</th><td>{synthetic[f].test_mae.toFixed(3)}</td><td>{synthetic[f].test_rmse?.toFixed(3) ?? "Unavailable"}</td><td>{synthetic[f].test_r2.toFixed(3)}</td><td>{(synthetic[f].test_interval_coverage*100).toFixed(1)}%</td></tr>)}</tbody></table></div> : <p>Loading active release metrics…</p>}<p className="feature-help">Generated records only. These numbers do not establish farm accuracy and cannot be ranked directly against the real-data study below.</p></section>
    <section className="feature-card"><h2>Real-source rice research · not deployed</h2>{error ? <p role="alert">{error} <button className="btn-ghost" onClick={() => setRetry(n => n+1)}>Retry</button></p> : !data ? <p role="status">Loading development results…</p> : <><p>{data.scope}</p><p className="feature-notice">Final reserved cohorts remain unscored. Publication readiness and quantum advantage have not been established.</p><label>Investigation<select value={runId} onChange={e => { setRunId(e.target.value); setModelIndex(0); }}>{data.runs.map(r => <option key={r.id} value={r.id}>{r.title}</option>)}</select></label>{run?.status !== "available" ? <p>This result artifact is unavailable on this installation.</p> : <><div className="feature-table-scroll"><table><thead><tr><th>Model / inputs</th><th>MAE</th><th>RMSE ± SD</th><th>R²</th><th>Coverage</th><th>Width</th></tr></thead><tbody>{run.models.map(m => <tr key={`${m.family}-${m.variant}`}><th>{label(m.family)}<small>{label(m.variant)} · {m.splits} splits</small></th><td>{m.mae.toFixed(3)}</td><td>{m.rmse.toFixed(3)} ± {m.rmse_sd.toFixed(3)}</td><td>{m.r2.toFixed(3)}</td><td>{(m.coverage_90*100).toFixed(1)}%</td><td>{m.width_90_q_ha.toFixed(3)}</td></tr>)}</tbody></table></div><p className="feature-help">Errors and interval widths in q/ha. SD is across overlapping splits, not a confidence interval. Every tuned family had the same 25-candidate budget.</p><h3>Where does it struggle?</h3><div className="feature-two"><label>Model and input condition<select value={modelIndex} onChange={e => setModelIndex(Number(e.target.value))}>{run.models.map((m, i) => <option value={i} key={`${m.family}-${m.variant}`}>{label(m.family)} · {label(m.variant)}</option>)}</select></label><label>Breakdown<select value={dimension} onChange={e => setDimension(e.target.value)}><option value="district">District</option><option value="year">Year</option></select></label></div>{model && <div className="evidence-bars">{model.breakdown[dimension].map(r => <div key={r.label}><span>{r.label}</span><meter min="0" max={Math.max(...model.breakdown[dimension].map(v => v.rmse), 1)} value={r.rmse} /><strong>{r.rmse.toFixed(2)} q/ha</strong><small>{r.prediction_count} predictions</small></div>)}</div>}<p className="feature-help">Pooled saved development predictions; a row may appear in multiple splits. Counts are predictions, not independent observations. Historical district IDs do not imply current administrative boundaries.</p><p className="release-note">Artifact: {run.directory}</p></>}<h3>Data provenance and limitations</h3><ul>{data.sources.map(source => <li key={source}>{source}</li>)}</ul><p className="feature-help">{data.limitations}</p></>}</section>
  </main>;
}
