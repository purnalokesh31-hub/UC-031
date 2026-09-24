import { Activity, Info } from "lucide-react";

export default function MetricsBadge({ metrics, apiStatus }) {
  if (!metrics) return <section className="validation-panel"><p>Model evaluation details are unavailable.</p></section>;
  const selected = metrics.selected_family;
  return (
    <details className="validation-panel" aria-labelledby="validation-title">
      <summary className="validation-heading">
        <div className="validation-title-wrap">
          <div className="validation-icon"><Activity size={17} /></div>
          <div><p className="output-eyebrow">MODEL CHECK · {metrics.crop_type.toUpperCase()}</p><h2 id="validation-title">Evaluation & regression scores</h2></div>
        </div>
        <span className={`validation-api validation-api-${apiStatus}`}>{apiStatus === "online" ? "Model service online" : apiStatus === "offline" ? "Model service offline" : "Checking service"}</span>
      </summary>
      <p className="validation-intro">Both models were evaluated on the same {metrics.classical.test_samples} held-out synthetic records. The model used for estimates is chosen using cross-validation.</p>
      <div className="validation-model-grid">
        {["classical", "quantum"].map(family => {
          const m = metrics[family];
          const isSelected = family === selected;
          return (
            <article className={`validation-model${isSelected ? " validation-model-selected" : ""}`} key={family}>
              <div className="validation-model-title"><h3>{family === "classical" ? "Classical" : "Quantum simulation"}</h3>{isSelected && <span>Used for estimate</span>}</div>
              <p className="validation-estimator">{m.name}</p>
              <div className="validation-stats">
                <div><strong>{m.test_mae.toFixed(2)}</strong><span>Average error · q/ha</span></div>
                <div><strong>{m.test_r2.toFixed(3)}</strong><span>R² on held-out data</span></div>
                <div><strong>{(m.test_interval_coverage * 100).toFixed(0)}%</strong><span>Interval coverage</span></div>
              </div>
            </article>
          );
        })}
      </div>
      <div className="validation-note"><Info size={15} /><p><strong>Important:</strong> {metrics.scope || "Synthetic data; no field validation."} These scores describe this generated dataset only. Real accuracy needs independent harvest records from farms and seasons not used during training.</p></div>
    </details>
  );
}
