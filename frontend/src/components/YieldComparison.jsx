import { useEffect, useState } from "react";
import { AlertTriangle, ArrowDownToLine, Atom, Check, Info, Layers, Pencil, Ruler, Sprout, Sliders, ChevronDown } from "lucide-react";
import { ACRES_PER_HECTARE, formatAmount, formatYield, harvestForArea, intervalScale } from "../lib/yieldDisplay";

const FAMILIES = [
  { key: "classical", label: "Classical", icon: Layers, color: "#10b981" },
  { key: "quantum", label: "Quantum simulation", icon: Atom, color: "#6366f1" },
];

const INPUT_NAMES = {
  N: "Nitrogen (kg/ha)",
  P: "Phosphorus (kg/ha)",
  K: "Potassium (kg/ha)",
  pH: "Soil pH",
  moisture: "Soil moisture (%)",
  temperature: "Temperature (°C)",
  humidity: "Humidity (%)",
  rainfall: "Rainfall (mm)",
};

export default function YieldComparison({ result, isLoading, onEdit }) {
  const [unit, setUnit] = useState("t");
  const [area, setArea] = useState(String(result?.context?.area || "1"));
  const [areaUnit, setAreaUnit] = useState(result?.context?.areaUnit || "ha");
  const [compareSplit, setCompareSplit] = useState(50); // 0 = 100% classical, 100 = 100% quantum

  useEffect(() => {
    if (result?.id) {
      setArea(String(result.context?.area || "1"));
      setAreaUnit(result.context?.areaUnit || "ha");
    }
  }, [result?.id]);

  if (isLoading) {
    return (
      <div className="output-placeholder output-loading" role="status">
        <span className="loading-mark" />
        <h2>Analyzing Your Scenario</h2>
        <p>Evaluating classical and simulated quantum models on the same field inputs…</p>
        <div className="loading-line" />
      </div>
    );
  }

  if (!result) return null;

  const selected = result.recommended;
  const selectedFamily = result.selected_family;
  const predictions = FAMILIES.map(({ key }) => result[key]).filter(Boolean);
  const scale = intervalScale(predictions);
  const outside = result.out_of_distribution;
  const validPoint = Number.isFinite(selected.yield_qph) && selected.yield_qph > 0;
  const intervalAvailable = validPoint && !outside && Number.isFinite(selected.confidence_low) && Number.isFinite(selected.confidence_high);
  const suffix = unit === "t" ? "t/ha" : "q/ha";
  const harvest = harvestForArea(selected, area, areaUnit, outside);
  const numericArea = Number(area);
  const areaValid = area !== "" && Number.isFinite(numericArea) && numericArea > 0 && numericArea <= 1000000;
  const inputs = Object.entries(result.inputs || {}).filter(([key]) => key !== "crop_type");
  const difference = result.classical && result.quantum ? Math.abs(result.classical.yield_qph - result.quantum.yield_qph) : null;

  const reportText = [
    "CROPGUARD — YIELD SCENARIO REPORT",
    `Crop: ${result.crop_type}`,
    `Created: ${new Date(result.created_at).toLocaleString()}`,
    "Data basis: synthetic training and evaluation records; field accuracy is not established.",
    "",
    `Selected model: ${selected.model} (chosen by training cross-validation)`,
    `Estimated yield: ${validPoint ? formatYield(selected.yield_qph, unit) + " " + suffix : "Unavailable — nonpositive model output"}`,
    `90% prediction interval: ${intervalAvailable ? formatYield(selected.confidence_low, unit) + "–" + formatYield(selected.confidence_high, unit) + " " + suffix : "Unavailable"}`,
    `Field area: ${area} ${areaUnit}`,
    `Estimated field total: ${harvest ? formatAmount(harvest.tonnes) + " tonnes" : "Unavailable"}`,
    ...(harvest?.low != null ? [`Scaled interval: ${formatAmount(harvest.low)}–${formatAmount(harvest.high)} tonnes`] : []),
    "Field totals assume uniform yield; area is not a model input.",
    "",
    "MODEL COMPARISON",
    ...FAMILIES.filter(({ key }) => result[key]).map(
      ({ key, label }) =>
        `${label}: ${formatYield(result[key].yield_qph, unit)} ${suffix}; CV RMSE ${result.metrics[key].cv_rmse.toFixed(3)} q/ha; holdout MAE ${result.metrics[key].test_mae.toFixed(3)} q/ha; holdout R² ${result.metrics[key].test_r2.toFixed(4)}`
    ),
    "",
    `Field: ${result.context?.fieldName || "Unassigned"}`,
    `Growing period: ${result.context?.start || "Not entered"} to ${result.context?.end || "Not entered"}`,
    "FIELD INPUTS",
    ...inputs.map(
      ([key, value]) =>
        `${INPUT_NAMES[key] || key}: ${value}; source: ${result.context?.sources?.[key]?.type || "sample"}; date: ${result.context?.sources?.[key]?.date || "Not entered"}`
    ),
    "",
    "LIMITATIONS",
    ...(result.warnings || []),
    "Quantum kernel is simulated classically. Model agreement does not establish accuracy or quantum advantage.",
    "R² is not a percentage of correct predictions. Prediction intervals are calibrated on synthetic records.",
    `Model release: ${result.release_id}`,
  ].join("\n");

  return (
    <div className="yield-output">
      {/* Primary Result Card */}
      <section className={`analysis-result${outside || !validPoint ? " analysis-extrapolation" : ""}`} aria-labelledby="outlook-heading">
        <div className="result-header">
          <div className="result-crop-icon"><Sprout size={24} /></div>
          <div>
            <p className="output-eyebrow">YIELD OUTLOOK · ESTIMATE READY</p>
            <h2 id="outlook-heading">{result.crop_type} Predicted Yield</h2>
          </div>
          <span className="result-status">
            {!validPoint ? "⚠️ Review Inputs" : outside ? "⚠️ Extrapolation" : "✨ Analysis Complete"}
          </span>
        </div>

        <div className="result-main">
          <div className="result-value-heading">
            <span>Estimated Yield per Hectare</span>
            <div className="unit-toggle" role="group" aria-label="Yield display unit">
              <button
                type="button"
                className={unit === "t" ? "active" : ""}
                aria-pressed={unit === "t"}
                onClick={() => setUnit("t")}
                aria-label="Tonnes per hectare"
              >
                t/ha
              </button>
              <button
                type="button"
                className={unit === "q" ? "active" : ""}
                aria-pressed={unit === "q"}
                onClick={() => setUnit("q")}
                aria-label="Quintals per hectare"
              >
                q/ha
              </button>
            </div>
          </div>

          <p className="yield-headline">
            {validPoint ? formatYield(selected.yield_qph, unit) : "Unavailable"}
            <span>{validPoint && suffix}</span>
          </p>

          <p className="yield-conversion">
            {validPoint
              ? `${formatYield(selected.yield_qph, unit === "t" ? "q" : "t")} ${unit === "t" ? "quintals" : "tonnes"} per hectare`
              : "The model produced a nonpositive yield. Review the inputs."}
          </p>

          <div className="yield-range">
            <div>
              <span>90% Prediction Interval</span>
              <strong>
                {intervalAvailable
                  ? `${formatYield(selected.confidence_low, unit)}–${formatYield(selected.confidence_high, unit)} ${suffix}`
                  : "Unavailable for these inputs"}
              </strong>
            </div>
            <Info size={18} />
            <p>
              {intervalAvailable
                ? "Calibrated on synthetic records with 90% conformal coverage."
                : "Inputs outside model training coverage cannot support calibrated prediction bounds."}
            </p>
          </div>

          <p className="model-selection">
            <Check size={16} />
            <span>
              <strong>{selectedFamily === "classical" ? "Classical Pipeline" : "Quantum Simulation"}</strong> chosen via lowest training cross-validation RMSE.
            </span>
          </p>
        </div>

        {(outside || !validPoint) && (
          <div className="extrapolation-notice" role="status">
            <AlertTriangle size={20} />
            <div>
              <strong>Review This Scenario Before Relying on Outputs</strong>
              <p>
                {outside
                  ? `Outside model training coverage on: ${(result.out_of_range_features || []).map(key => INPUT_NAMES[key] || key).join(", ")}. Calibrated intervals withheld.`
                  : "A positive physical yield could not be estimated."}
              </p>
            </div>
          </div>
        )}

        <div className="result-toolbar">
          <button type="button" className="btn-ghost" onClick={onEdit}>
            <Pencil size={15} /> Edit Inputs
          </button>
          <a
            className="export-button"
            href={`data:text/plain;charset=utf-8,${encodeURIComponent(reportText)}`}
            download={`cropguard-${result.crop_type.toLowerCase()}-report.txt`}
          >
            <ArrowDownToLine size={16} /> Export Scenario Report
          </a>
        </div>
      </section>

      {/* Interactive Harvest Area Slider Card */}
      <section className="harvest-card" aria-labelledby="harvest-title">
        <div className="section-card-heading">
          <Ruler size={20} />
          <h3 id="harvest-title">Interactive Field Harvest Calculator</h3>
        </div>

        <div className="harvest-layout">
          <div>
            <label htmlFor="field-area">
              <span>Field Area</span>
              <small className="text-gray-500">(Slide or type)</small>
            </label>
            <div className="area-control">
              <input
                id="field-area"
                type="number"
                inputMode="decimal"
                min="0"
                step="any"
                value={area}
                onChange={event => setArea(event.target.value)}
                aria-invalid={!areaValid || undefined}
                aria-describedby="area-help"
              />
              <select
                aria-label="Field area unit"
                value={areaUnit}
                onChange={event => {
                  const val = Number(area);
                  if (areaValid) {
                    setArea(
                      String(
                        Number(
                          (event.target.value === "acre" ? val * ACRES_PER_HECTARE : val / ACRES_PER_HECTARE).toPrecision(12)
                        )
                      )
                    );
                  }
                  setAreaUnit(event.target.value);
                }}
              >
                <option value="ha">Hectares</option>
                <option value="acre">Acres</option>
              </select>
            </div>

            {/* Area Interactive Slider */}
            <div className="parameter-slider-wrapper mt-3">
              <div className="slider-track-container">
                <div className="slider-visual-track">
                  <div
                    className="slider-visual-progress"
                    style={{
                      width: `${Math.min(100, Math.max(0, ((Math.min(50, Number(area) || 1) - 0.5) / 49.5) * 100))}%`,
                    }}
                  />
                </div>
                <input
                  type="range"
                  min="0.5"
                  max="50"
                  step="0.5"
                  value={Math.min(50, Math.max(0.5, Number(area) || 1))}
                  onChange={e => setArea(e.target.value)}
                  className="parameter-slider-interactive"
                  aria-label="Slide to adjust field area"
                />
              </div>
              <div className="slider-snap-chips">
                <button type="button" className="slider-snap-chip" onClick={() => setArea("1")}>1 {areaUnit}</button>
                <button type="button" className="slider-snap-chip" onClick={() => setArea("5")}>5 {areaUnit}</button>
                <button type="button" className="slider-snap-chip" onClick={() => setArea("10")}>10 {areaUnit}</button>
                <button type="button" className="slider-snap-chip" onClick={() => setArea("25")}>25 {areaUnit}</button>
              </div>
            </div>
          </div>

          <div className="harvest-total" aria-live="polite">
            <span>Total Harvest Projection</span>
            <strong>
              {harvest ? `${formatAmount(harvest.tonnes)}` : "—"}
              <small>{harvest && " tonnes"}</small>
            </strong>
          </div>
        </div>

        <p id="area-help">
          {!areaValid
            ? "Enter an area greater than 0 and at most 1,000,000."
            : outside || !validPoint
            ? "Total harvest is withheld for out-of-coverage inputs."
            : `Assumes uniform yield across parcel. ${
                harvest?.low != null ? `Scaled 90% range: ${formatAmount(harvest.low)}–${formatAmount(harvest.high)} tonnes.` : ""
              }`}
        </p>
      </section>

      {/* Model Comparison Details with Dual Comparison Slider */}
      <details className="comparison-card model-comparison-details" open>
        <summary>
          <span>Model Comparison · Classical vs Simulated Quantum</span>
          <ChevronDown size={16} />
        </summary>

        <div aria-labelledby="comparison-title" className="pt-3">
          <div className="comparison-header">
            <div>
              <p className="output-eyebrow">SAME INPUTS · TWO PARADIGMS</p>
              <h2 id="comparison-title">Classical vs Quantum Comparison</h2>
            </div>
            <span className="comparison-unit">{suffix}</span>
          </div>

          {/* Model Comparison Tiles */}
          <div className="comparison-tiles">
            {FAMILIES.map(({ key, label, icon: Icon, color }) => {
              const prediction = result[key];
              if (!prediction) return null;
              const isRecommended = key === selectedFamily;
              return (
                <article
                  key={key}
                  className={`comparison-tile tile-${key}${isRecommended ? " tile-selected" : ""}`}
                >
                  <div className="comparison-tile-label">
                    <Icon size={18} style={{ color }} />
                    <h3>{label}</h3>
                  </div>
                  <strong>
                    {formatYield(prediction.yield_qph, unit)}
                    <small> {suffix}</small>
                  </strong>
                  <p>
                    {isRecommended ? (
                      <><Check size={14} /> Selected Model (Best CV)</>
                    ) : (
                      "Alternative Candidate"
                    )}
                  </p>
                  {result.metrics?.[key] && (
                    <div className="tile-metrics-mini">
                      <span>CV RMSE: {result.metrics[key].cv_rmse.toFixed(2)}</span>
                      <span>Holdout R²: {result.metrics[key].test_r2.toFixed(3)}</span>
                    </div>
                  )}
                </article>
              );
            })}
          </div>

          {/* Interactive Crossfader / Comparison Slider */}
          {result.classical && result.quantum && (
            <div className="model-crossfader-box">
              <div className="crossfader-labels">
                <span className={compareSplit < 40 ? "font-bold text-emerald-700" : "text-gray-500"}>
                  🌿 Classical Emphasis
                </span>
                <span className="text-xs text-gray-400 font-mono">
                  Δ Difference: {difference != null ? `${formatYield(difference, unit)} ${suffix}` : "—"}
                </span>
                <span className={compareSplit > 60 ? "font-bold text-indigo-700" : "text-gray-500"}>
                  ⚛️ Quantum Emphasis
                </span>
              </div>
              <div className="parameter-slider-wrapper">
                <div className="slider-track-container">
                  <div className="slider-visual-track">
                    <div
                      className="slider-visual-progress"
                      style={{
                        background: "linear-gradient(90deg, #10b981 0%, #6366f1 100%)",
                        width: `${compareSplit}%`,
                      }}
                    />
                  </div>
                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={compareSplit}
                    onChange={e => setCompareSplit(Number(e.target.value))}
                    className="parameter-slider-interactive"
                    aria-label="Slide to compare classical and quantum models"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Interval Bounds Chart */}
          {!outside && scale && (
            <div
              className="interval-chart"
              role="img"
              aria-label="Prediction intervals on a shared yield axis"
            >
              {FAMILIES.map(({ key, label }) => {
                const p = result[key];
                if (!p || !Number.isFinite(p.confidence_low) || !Number.isFinite(p.confidence_high)) return null;
                return (
                  <div className={`interval-row interval-${key}`} key={key}>
                    <span>{label}</span>
                    <div className="interval-track">
                      <i
                        style={{
                          left: `${scale.position(p.confidence_low)}%`,
                          width: `${scale.position(p.confidence_high) - scale.position(p.confidence_low)}%`,
                        }}
                      />
                      <b style={{ left: `${scale.position(p.yield_qph)}%` }} />
                      <span className="sr-only">
                        {formatYield(p.confidence_low, unit)} to {formatYield(p.confidence_high, unit)} {suffix}
                      </span>
                    </div>
                  </div>
                );
              })}
              <div className="interval-axis">
                <span>{formatYield(scale.min, unit)} {suffix}</span>
                <span>90% Conformal Range</span>
                <span>{formatYield(scale.max, unit)} {suffix}</span>
              </div>
            </div>
          )}

          <p className="comparison-footnote">
            {difference != null && (
              <>Model predictions differ by <strong>{formatYield(difference, unit)} {suffix}</strong>. </>
            )}
            Simulated quantum kernel executes via classical linear algebra on 4 qubits.
          </p>
        </div>
      </details>

      {/* Inputs & Report Details Drawer/Accordion */}
      <details className="scenario-details">
        <summary>
          <span>Input Snapshot & Provenance Report</span>
          <ChevronDown size={16} />
        </summary>
        <dl className="scenario-values">
          {inputs.map(([key, value]) => (
            <div key={key}>
              <dt>{INPUT_NAMES[key] || key}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>
        <p className="release-note">Model Release: {result.release_id}</p>
        <pre className="report-preview">{reportText}</pre>
      </details>
    </div>
  );
}
