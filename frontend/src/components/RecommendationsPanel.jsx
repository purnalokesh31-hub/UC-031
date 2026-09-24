import { motion } from "framer-motion";
import { Leaf, AlertTriangle, CheckCircle, Thermometer, Bug, FlaskConical } from "lucide-react";

export default function RecommendationsPanel({ data, isLoading }) {
  if (!data && !isLoading) {
    return (
      <div className="card" style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", minHeight: 210, padding: 28, textAlign: "center",
      }}>
        <div style={{
          width: 52, height: 52, borderRadius: "50%",
          background: "linear-gradient(135deg, var(--g100), var(--g50))",
          border: "2px dashed var(--g300)",
          display: "flex", alignItems: "center", justifyContent: "center",
          marginBottom: 14, boxShadow: "0 0 0 6px rgba(34,197,94,0.06)",
        }}>
          <Leaf size={22} color="var(--g500)" />
        </div>
        <p style={{ fontWeight: 700, color: "var(--text-800)", fontSize: "0.86rem", margin: "0 0 5px" }}>
          Yield context
        </p>
        <p style={{ color: "var(--text-400)", fontSize: "0.74rem" }}>A demo baseline comparison appears with your estimate.</p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="card" style={{
        display: "flex", flexDirection: "column", alignItems: "center",
        justifyContent: "center", minHeight: 200, padding: 28, textAlign: "center", gap: 12,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: "50%",
          border: "3px solid var(--g200)", borderTopColor: "var(--g500)",
          animation: "spin 0.85s linear infinite",
        }} />
        <p style={{ color: "var(--text-400)", fontSize: "0.77rem" }}>Generating recommendations…</p>
      </div>
    );
  }

  const {
    crop: cropName, predicted_yield_qph, baseline_yield_qph, yield_ratio,
    severity, npk_deficiencies, weather_alerts, pest_interventions
  } = data;

  const alertClass = severity === "critical" ? "alert-red" : severity !== "normal" ? "alert-yellow" : "alert-green";
  const alertIcon  = severity !== "normal" ? <AlertTriangle size={14} /> : <CheckCircle size={14} />;
  const alertMsg   = severity === "unassessed" ? "Yield alert unavailable — outside the training range" : severity === "critical"
    ? "Estimate below the demo critical-yield threshold"
    : severity === "warning"
    ? "Estimate below the demo warning threshold"
    : "Estimate within the demo baseline range";

  return (
    <motion.div
      initial={{ opacity: 0, x: 12 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
      style={{ display: "flex", flexDirection: "column", gap: 12 }}
    >
      {/* Yield summary */}
      <div className="card">
        <div className="card-header">
          <div className="icon-circle"><Leaf size={15} /></div>
          <div>
            <div className="card-title">{cropName} — Yield context</div>
            <div style={{ fontSize: "0.7rem", color: "var(--text-500)", marginTop: 1 }}>Demo baseline rules · {data.prediction_model}</div>
          </div>
        </div>
        <div className="card-body">
          <div className={alertClass} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 14 }}>
            {alertIcon} {alertMsg}
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, textAlign: "center" }}>
            {[
              { lbl: "Predicted", val: predicted_yield_qph, color: "var(--g700)" },
              { lbl: "Baseline",  val: baseline_yield_qph,  color: "var(--text-700)"  },
              {
                lbl: "Ratio", val: `${(yield_ratio * 100).toFixed(0)}%`,
                color: yield_ratio < 0.5 ? "var(--red500)" : yield_ratio < 0.75 ? "#92400e" : "var(--g700)",
              },
            ].map(({ lbl, val, color }) => (
              <div key={lbl} style={{
                background: "var(--bg-subtle)", border: "1px solid var(--border)",
                borderRadius: 10, padding: "10px 6px",
              }}>
                <div style={{ fontSize: "1.05rem", fontWeight: 800, color, fontFamily: "JetBrains Mono, monospace", lineHeight: 1 }}>{val}</div>
                <div style={{ fontSize: "0.60rem", color: "var(--text-400)", marginTop: 4, textTransform: "uppercase", letterSpacing: 0.4, fontWeight: 600 }}>{lbl}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* NPK deficiencies */}
      {npk_deficiencies.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="icon-circle" style={{ background: "var(--amber-50)", color: "#92400e", borderColor: "#fde68a" }}>
              <FlaskConical size={14} />
            </div>
            <div className="card-title">Nutrient Deficiencies</div>
          </div>
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {npk_deficiencies.map((d, i) => (
              <div key={i} style={{
                background: "var(--amb50)", border: "1px solid #fde68a",
                borderLeft: "3px solid var(--amb500)",
                borderRadius: 10, padding: 11,
              }}>
                <div style={{ marginBottom: 5 }}><span className="badge badge-orange">{d.nutrient} Deficiency</span></div>
                <p style={{ fontSize: "0.74rem", color: "#78350f", marginBottom: 4 }}>{d.symptom}</p>
                <p style={{ fontSize: "0.74rem", color: "var(--text-700)" }}><strong>Remedy:</strong> {d.remedy}</p>
                {d.organic_alternative && (
                  <p style={{ fontSize: "0.71rem", color: "var(--g700)", marginTop: 4 }}>🌿 {d.organic_alternative}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Weather alerts */}
      {weather_alerts.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="icon-circle" style={{ background: "var(--red-50)", color: "var(--red-500)", borderColor: "#fca5a5" }}>
              <Thermometer size={14} />
            </div>
            <div className="card-title">Weather Stress</div>
          </div>
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {weather_alerts.map((a, i) => (
              <div key={i} style={{
                background: "var(--red50)", border: "1px solid #fecaca",
                borderLeft: "3px solid var(--red500)",
                borderRadius: 10, padding: 11,
              }}>
                <span className="badge badge-red" style={{ marginBottom: 7 }}>{a.type.replace(/_/g, " ")}</span>
                <p style={{ fontSize: "0.74rem", color: "var(--text-700)", marginTop: 7 }}>{a.remedy}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pest management */}
      {pest_interventions.length > 0 && (
        <div className="card">
          <div className="card-header">
            <div className="icon-circle" style={{ background: "#f5f3ff", color: "#5b21b6", borderColor: "#ddd6fe" }}>
              <Bug size={14} />
            </div>
            <div className="card-title">Pest Management</div>
          </div>
          <div className="card-body" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {pest_interventions.slice(0, 2).map((p, i) => (
              <div key={i} style={{
                border: "1px solid #ddd6fe", background: "#f5f3ff",
                borderLeft: "3px solid #7c3aed",
                borderRadius: 10, padding: 11,
              }}>
                <p style={{ fontSize: "0.77rem", fontWeight: 700, color: "#5b21b6", marginBottom: 6 }}>{p.pest}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--text-700)" }}>🧪 {p.chemical}</p>
                <p style={{ fontSize: "0.72rem", color: "var(--g700)", marginTop: 4 }}>🌿 {p.bio}</p>
              </div>
            ))}
            <p style={{ fontSize: "0.62rem", color: "var(--text-300)", textAlign: "center", marginTop: 2, letterSpacing: "0.3px" }}>
              Source: ICAR / AP Agriculture Dept
            </p>
          </div>
        </div>
      )}

      {/* All good */}
      {severity === "normal" && npk_deficiencies.length === 0 && weather_alerts.length === 0 && (
        <div className="alert-green" style={{ textAlign: "center" }}>
          <CheckCircle size={18} style={{ margin: "0 auto 6px", display: "block" }} />
          <strong>Yield estimate only</strong><br />
          <span style={{ fontSize: "0.78rem" }}>{data.assessment_note}</span>
        </div>
      )}
    </motion.div>
  );
}
