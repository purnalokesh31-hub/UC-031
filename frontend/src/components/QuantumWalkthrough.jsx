import { useEffect, useState } from "react";
import { api } from "../api";

const steps = ["Scale inputs", "Encode the circuit", "Compare similarities", "Estimate yield"];
export default function QuantumWalkthrough({ result }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState(0);
  const [trace, setTrace] = useState(null);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (!open) return;
    const controller = new AbortController();
    setTrace(null); setError("");
    api.post("/quantum/walkthrough", result.inputs, { signal: controller.signal }).then(({ data }) => {
      if (data.release_id !== result.release_id) throw Error("The model release changed. Run a new analysis before exploring its circuit.");
      setTrace(data);
    }).catch(e => { if (!controller.signal.aborted) setError(e.message?.startsWith("The model release") ? e.message : "The walkthrough could not load. Check the connection and retry."); });
    return () => controller.abort();
  }, [open, result.id, retry]);
  return <details className="feature-card quantum-walkthrough" open={open} onToggle={e => setOpen(e.currentTarget.open)}><summary>Explore how the quantum model produced this estimate</summary>
    {open && <>{error ? <p role="alert">{error} <button className="btn-ghost" onClick={() => setRetry(n => n+1)}>Retry</button></p> : !trace ? <p role="status">Loading the actual circuit calculation…</p> : <>
      <p className="feature-help">Exact classical simulation · {trace.qubits} qubits · {trace.layers} encoding layers. This walkthrough uses your inputs and the model release behind this analysis.</p>
      <div className="walkthrough-tabs" role="group" aria-label="Walkthrough steps">{steps.map((label, i) => <button type="button" key={label} aria-pressed={step === i} onClick={() => setStep(i)}>{i+1}. {label}</button>)}</div>
      <div className="parameter-slider-wrapper" style={{ margin: "10px 0 16px" }}>
        <div className="slider-track-container">
          <div className="slider-visual-track">
            <div className="slider-visual-progress" style={{ width: `${(step / 3) * 100}%`, background: "linear-gradient(90deg, #6366f1 0%, #38bdf8 100%)" }} />
          </div>
          <input
            type="range"
            min="0"
            max="3"
            step="1"
            value={step}
            onChange={e => setStep(Number(e.target.value))}
            className="parameter-slider-interactive"
            aria-label="Slide through quantum simulation pipeline steps"
          />
        </div>
      </div>
      <section aria-live="polite"><h3>{steps[step]}</h3>
        {step === 0 && <><p>Each input is standardized using the training-set mean and spread. The current input does not refit the scaler.</p><div className="feature-table-scroll"><table><thead><tr><th>Input</th><th>Raw value</th><th>Standardized</th></tr></thead><tbody>{trace.features.map(f => <tr key={f.name}><th>{f.name}</th><td>{f.raw}</td><td>{f.standardized.toFixed(3)}</td></tr>)}</tbody></table></div></>}
        {step === 1 && <><p>RY and RZ rotations encode the eight features. CNOT gates connect qubits 0→1→2→3 after each encoding layer. Angles below include the RY offset of π/2.</p><div className="circuit-lines">{[0,1,2,3].map(q => <div key={q}><span>q{q} |0⟩</span><b>RY {trace.features[q].rotation_radians.toFixed(3)}</b><b>RZ {trace.features[q+4].rotation_radians.toFixed(3)}</b><span>→ CNOT chain</span></div>)}</div><p className="feature-help">Repeat this layer {trace.layers} times. Final basis probabilities, ordered q3q2q1q0; these are not yield confidence scores.</p><div className="probability-grid">{trace.probabilities.map(p => <div key={p.basis}><label>{p.basis} · {(p.probability*100).toFixed(1)}%</label><meter min="0" max="1" value={p.probability}>{p.probability}</meter></div>)}</div></>}
        {step === 2 && <><p>The fidelity kernel uses K(x,z) = |⟨ψ(x)|ψ(z)⟩|² to compare this circuit state with {trace.reference_count} stored synthetic training states.</p><div className="similarity-list">{trace.neighbors.map(n => <div key={n.reference}><span>Reference #{n.reference}</span><meter min="0" max="1" value={n.fidelity} /><strong>{n.fidelity.toFixed(6)}</strong></div>)}</div><p className="feature-help">Five highest uncentered similarities. High similarity does not mean a prediction is accurate. The model uses all reference states, not just these five.</p></>}
        {step === 3 && <><p>{trace.centered ? "The kernel is centered using training statistics." : "The kernel is not centered."} Kernel ridge regression combines the similarities using learned weights, then reverses target scaling.</p><p className="walkthrough-yield">{trace.yield_qph.toFixed(2)} <span>q/ha</span></p><p>Regularization α = {trace.alpha}; angle scale = {trace.angle_scale}.</p><p className="feature-help">The prediction interval is calibrated separately. It does not come from measuring these qubits. No quantum hardware or computational advantage is demonstrated.</p></>}
      </section><div className="feature-actions"><button className="btn-ghost" disabled={step === 0} onClick={() => setStep(s => s-1)}>Previous</button><button className="btn-ghost" disabled={step === 3} onClick={() => setStep(s => s+1)}>Next step</button></div>
    </>}</>}
  </details>;
}
