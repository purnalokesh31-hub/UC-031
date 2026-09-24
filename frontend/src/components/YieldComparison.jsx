import { useState } from "react";
import { AlertTriangle, Check, Clock3, FileText, FlaskConical, Pencil, TrendingUp } from "lucide-react";

const FAMILIES = [
  { key: "classical", label: "Classical model", accent: "classical" },
  { key: "quantum", label: "Quantum simulation", accent: "quantum" },
];

export default function YieldComparison({ result, isLoading, comparison, comparisonLoading, onCompare, onEdit }) {
  const [showReport, setShowReport] = useState(false);
  if (isLoading) {
    return <div className="output-placeholder output-loading" role="status">
      <span className="loading-mark" />
      <h2>Calculating your estimate…</h2>
      <p>Running the model selected for this crop.</p>
    </div>;
  }
  if (!result) return null;

  const selected = result.recommended;
  const selectedFamily = result.selected_family;
  const selectedMetrics = result.metrics[selectedFamily];
  const comparisonFamily = selectedFamily === "classical" ? "quantum" : "classical";
  const maxYield = Math.max(1, selected.yield_qph, comparison?.data?.yield_qph || 0) * 1.12;
  const names = { N: "Nitrogen (kg/ha)", P: "Phosphorus (kg/ha)", K: "Potassium (kg/ha)", pH: "Soil pH", moisture: "Moisture (%)", temperature: "Temperature (°C)", humidity: "Humidity (%)", rainfall: "Rainfall (mm)" };
  const inputs = Object.entries(result.inputs || {}).filter(([key]) => key !== "crop_type");
  const reportText = ["CROPGUARD · FIELD SCENARIO REPORT", `Crop: ${result.crop_type}`, `Created: ${result.created_at}`,
    "", `Estimated yield: ${selected.yield_qph} quintals/hectare (1 quintal = 100 kg)`,
    `90% interval: ${result.out_of_distribution ? "Unavailable outside training range" : `${selected.confidence_low}–${selected.confidence_high} q/ha`}`,
    `Model: ${selected.model}`, `Holdout R²: ${selectedMetrics.test_r2.toFixed(4)}`, `Holdout mean absolute error: ${selectedMetrics.test_mae.toFixed(3)} q/ha`,
    ...(comparison ? [`Comparison model: ${comparison.data.model}`, `Comparison yield: ${comparison.data.yield_qph} q/ha`] : []),
    "", "FIELD VALUES", ...inputs.map(([key, value]) => `${names[key]}: ${value}`), "", "LIMITS", ...result.warnings,
    "R² is not a percentage of correct predictions. This research estimate is not field-validated advice.", "", `Model release: ${result.release_id}`].join("\n");

  return (
    <div className="yield-output">
      <section className="estimate-card">
        <div className="estimate-card-top">
          <div>
            <p className="output-eyebrow">02 / YOUR ESTIMATE</p>
            <h2>{result.crop_type} yield outlook</h2>
          </div>
          <span className="selected-model"><Check size={14} /> {selectedFamily === "classical" ? "Classical" : "Quantum simulation"} selected</span>
        </div>
        <div className="estimate-number">{Number(selected.yield_qph).toFixed(1)} <span>q/ha</span></div>
        <p className="estimate-unit-help">Quintals per hectare · 1 quintal = 100 kg</p>
        <div className="estimate-foot">
          <span>90% interval · synthetic-data calibration</span>
          {result.out_of_distribution ? <strong>Unavailable outside training range</strong> :
            <strong>{selected.confidence_low}–{selected.confidence_high} q/ha</strong>}
        </div>
        <div className="selection-note">
          <TrendingUp size={15} />
          <span>{selected.model} was selected using the lowest cross-validation error on training data.</span>
        </div>
        {result.warnings.map(warning => <p key={warning} className="result-warning"><AlertTriangle size={15} />{warning}</p>)}
      </section>

      <div className="result-actions">
        <button type="button" className="btn-ghost" onClick={onEdit}><Pencil size={16} /> Edit field</button>
        <button type="button" className="btn-ghost" aria-expanded={showReport} aria-controls="scenario-report" onClick={() => setShowReport(value => !value)}><FileText size={16} /> {showReport ? "Close report" : "View report"}</button>
      </div>

      {showReport && <section id="scenario-report" className="scenario-report">
        <h3>Your scenario report</h3>
        <p>Download a copy, or select the text below to copy it.</p>
        <textarea aria-label="Scenario report text" value={reportText} readOnly rows={10} onFocus={event => event.target.select()} />
        <a className="btn-ghost" href={`data:text/plain;charset=utf-8,${encodeURIComponent(reportText)}`} download={`cropguard-${result.crop_type.toLowerCase()}.txt`}>Download report (.txt)</a>
      </section>}

      <details className="comparison-card">
        <summary className="comparison-heading"><div><p className="output-eyebrow">EXPLORE THE MODELS</p><h2>Compare classical & quantum</h2></div></summary>
        <p className="comparison-intro">Run the other model on these same field conditions. Compare its estimate, prediction interval and measured error.</p>
        <div className="model-comparison-list">
          {FAMILIES.map(({ key, label, accent }) => {
            const prediction = key === selectedFamily ? selected : comparison?.family === key ? comparison.data : null;
            const stats = result.metrics[key];
            const isSelected = selectedFamily === key;
            return (
              <article className={`model-row model-${accent}${isSelected ? " model-row-selected" : ""}`} key={key}>
                <div className="model-row-main">
                  <div className="model-name-wrap">
                    <span className={`model-marker marker-${accent}`} />
                    <div><h3>{label}{isSelected && <span className="chosen-label">Selected</span>}</h3><p>{stats.name}</p></div>
                  </div>
                  {prediction ? <strong className="model-yield">{Number(prediction.yield_qph).toFixed(1)} <small>q/ha</small></strong> :
                    <span className="comparison-not-run">Not run</span>}
                </div>
                {prediction && <>
                  <div className="model-bar-track" aria-label={`${label}: ${prediction.yield_qph} quintals per hectare`}>
                    <span className={`model-bar-fill bar-${accent}`} style={{ width: `${Math.max(2, Math.min(100, prediction.yield_qph / maxYield * 100))}%` }} />
                  </div>
                  <div className="model-interval">
                    <span>90% interval · demo calibration</span>
                    {result.out_of_distribution ? <strong>Unavailable</strong> :
                      <strong>{prediction.confidence_low}–{prediction.confidence_high} q/ha</strong>}
                  </div>
                </>}
                <div className="model-row-stats">
                  <span><b>CV RMSE</b> {stats.cv_rmse.toFixed(2)} q/ha</span>
                  <span><b>Hold-out MAE</b> {stats.test_mae.toFixed(2)} q/ha</span>
                  {prediction && <span className="model-latency"><Clock3 size={12} /> {prediction.inference_time_ms.toFixed(1)} ms</span>}
                  {comparisonLoading && key === comparisonFamily && <span className="model-latency" role="status">Calculating…</span>}
                </div>
                {!isSelected && !prediction && <button type="button" className="btn-ghost comparison-run" disabled={comparisonLoading}
                  onClick={() => onCompare(comparisonFamily)}>
                  <FlaskConical size={15} /> {comparisonLoading ? "Running comparison…" : `Run ${label.toLowerCase()} comparison`}
                </button>}
              </article>
            );
          })}
        </div>
        <p className="comparison-disclaimer">Scores and intervals describe generated records only. R² is not a percentage of correct predictions, and these results do not show how the model performs on a real farm.</p>
      </details>

      <details className="scenario-details">
        <summary>Field values used for this estimate</summary>
        <dl className="scenario-values">{inputs.map(([key, value]) => {
          return <div key={key}><dt>{names[key]}</dt><dd>{value}</dd></div>;
        })}</dl>
        <p className="release-note">Model release: {result.release_id}</p>
      </details>

      <div className="selected-quality-line">
        <span><Check size={14} /> Selected using cross-validation</span>
        <span>Hold-out R² {selectedMetrics.test_r2.toFixed(3)}</span>
        <span>Mean error {selectedMetrics.test_mae.toFixed(2)} q/ha</span>
      </div>
    </div>
  );
}
