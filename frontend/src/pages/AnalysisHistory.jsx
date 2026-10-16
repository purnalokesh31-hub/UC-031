import { useState } from "react";
import { useWorkspace, newId, toHectares, downloadJSON } from "../lib/WorkspaceStore";
import { formatAmount } from "../lib/yieldDisplay";

const units = { N: "kg/ha", P: "kg/ha", K: "kg/ha", pH: "", moisture: "%", temperature: "°C", humidity: "%", rainfall: "mm" };
export default function AnalysisHistory() {
  const { store, update, restore } = useWorkspace();
  const [selected, setSelected] = useState([]);
  const [crop, setCrop] = useState("");
  const [harvestFor, setHarvestFor] = useState("");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState("kg");
  const [area, setArea] = useState("");
  const [areaUnit, setAreaUnit] = useState("ha");
  const [date, setDate] = useState("");
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const compared = selected.map(id => store.history.find(r => r.id === id)).filter(Boolean);
  const harvestResult = store.history.find(r => r.id === harvestFor);
  const history = store.history.filter(r => !crop || r.crop_type === crop);
  function toggle(row) {
    if (selected.includes(row.id)) { setSelected(ids => ids.filter(id => id !== row.id)); return; }
    if (compared.length && compared[0].crop_type !== row.crop_type) { setMessage("Compare scenarios for the same crop. Clear the selection to choose a different crop."); return; }
    if (selected.length >= 3) { setMessage("Select up to three scenarios."); return; }
    setSelected(ids => [...ids, row.id]); setMessage("");
  }
  function chooseHarvest(row) {
    setHarvestFor(row.id);
    const existing = store.harvests.find(h => h.analysis_id === row.id);
    setQuantity(existing?.quantity ?? ""); setUnit(existing?.unit || "kg");
    setArea(existing?.area || row.context?.area || ""); setAreaUnit(existing?.areaUnit || row.context?.areaUnit || "ha");
    setDate(existing?.date || ""); setNote(existing?.note || ""); setMessage("");
    requestAnimationFrame(() => document.getElementById("harvest-record")?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }
  function saveHarvest(event) {
    event.preventDefault();
    const hectares = toHectares(area, areaUnit);
    if (!harvestResult || !Number.isFinite(hectares) || hectares <= 0 || !Number.isFinite(Number(quantity)) || Number(quantity) < 0 || quantity === "") { setMessage("Enter a valid harvested amount and area."); return; }
    const tonnes = Number(quantity) * ({ kg: .001, q: .1, t: 1 }[unit]);
    const record = { id: store.harvests.find(h => h.analysis_id === harvestFor)?.id || newId(), analysis_id: harvestFor,
      quantity, unit, area, areaUnit, date, note, actual_q_ha: tonnes * 10 / hectares, updated_at: new Date().toISOString() };
    update(current => ({ harvests: [...current.harvests.filter(h => h.analysis_id !== harvestFor), record] }));
    setMessage("Harvest record saved. This is a user-reported outcome, not independent model validation.");
  }
  return <main className="page-content notebook-page">
    <header className="feature-page-heading"><p className="dashboard-eyebrow">ANALYSIS HISTORY</p><h1>Compare scenarios. Learn from your harvest.</h1><p>Every successful analysis is saved with its input snapshot and model release. Comparisons describe model behaviour; changing an input does not establish a causal yield benefit.</p></header>
    {message && <p className="feature-notice" role="status">{message}</p>}
    <section className="feature-card"><div className="feature-section-top"><h2>Saved analyses ({store.history.length})</h2><label>Filter by crop<select value={crop} onChange={e => setCrop(e.target.value)}><option value="">All crops</option>{[...new Set(store.history.map(r => r.crop_type))].map(c => <option key={c}>{c}</option>)}</select></label><button className="btn-ghost" onClick={() => downloadJSON({ analyses: store.history, harvests: store.harvests }, "cropguard-analyses-and-harvests.json")}>Export records</button></div>
      {!history.length && <div className="feature-empty"><p>No saved analyses for this view.</p><a href="#dashboard">Create a yield analysis</a></div>}
      <div className="history-list">{history.map(row => <article key={row.id} className="notebook-item"><div className="feature-section-top"><label className="compare-choice"><input type="checkbox" checked={selected.includes(row.id)} onChange={() => toggle(row)} />Compare</label><h3>{row.context?.fieldName || "Unassigned field"} · {row.crop_type}</h3><span>{new Date(row.created_at).toLocaleString()}</span></div><p>Selected estimate: <strong>{formatAmount(row.recommended.yield_qph)} q/ha</strong> · {row.selected_family === "classical" ? "Classical" : "Quantum simulation"}{row.out_of_distribution && " · Outside training range"}</p><div className="feature-actions"><button className="btn-ghost" onClick={() => restore({ crop: row.crop_type, values: Object.fromEntries(Object.entries(row.inputs).filter(([key]) => key !== "crop_type")), sources: row.context?.sources || {}, context: row.context || {} })}>Reopen inputs</button><button className="btn-ghost" onClick={() => chooseHarvest(row)}>{store.harvests.some(h => h.analysis_id === row.id) ? "Edit harvest record" : "Record actual harvest"}</button><button className="btn-ghost" onClick={() => downloadJSON(row, `cropguard-analysis-${row.id}.json`)}>Export analysis</button></div><details><summary>Inputs, sources & model release</summary><p className="release-note">{row.release_id}</p><div className="feature-table-scroll"><table><thead><tr><th>Input</th><th>Value</th><th>Source</th><th>Date</th></tr></thead><tbody>{Object.entries(row.inputs).filter(([key]) => key !== "crop_type").map(([key, value]) => <tr key={key}><th>{key}</th><td>{value} {units[key]}</td><td>{row.context?.sources?.[key]?.type || "sample"}</td><td>{row.context?.sources?.[key]?.date || "Not entered"}</td></tr>)}</tbody></table></div>{row.context?.weather && <p className="feature-help">Attached weather context: {row.context.weather.source}, {row.context.weather.start}–{row.context.weather.end}. Weather was not substituted into the model inputs.</p>}</details></article>)}</div>
    </section>
    {!!compared.length && <section className="feature-card"><div className="feature-section-top"><h2>Scenario comparison</h2><button className="btn-ghost" onClick={() => setSelected([])}>Clear selection</button></div>{compared.length < 2 ? <p>Select one more analysis of the same crop to compare.</p> : <><p className="feature-help">All yields and intervals are q/ha. Changes are relative to the first selected scenario, using the same model family.</p>{new Set(compared.map(r => r.release_id)).size > 1 && <p className="feature-notice">Different model releases: differences may reflect model changes as well as inputs.</p>}<div className="feature-table-scroll"><table><thead><tr><th>Measurement</th>{compared.map((r, i) => <th key={r.id}>Scenario {i+1}<small>{r.context?.fieldName || r.crop_type}<br />{new Date(r.created_at).toLocaleString()}</small></th>)}</tr></thead><tbody>{["classical", "quantum"].map(family => <tr key={family}><th>{family === "classical" ? "Classical" : "Quantum simulation"}</th>{compared.map((r, i) => <td key={r.id}><strong>{formatAmount(r[family]?.yield_qph)}</strong><small>{Number.isFinite(r[family]?.confidence_low) ? `90% range ${formatAmount(r[family].confidence_low)}–${formatAmount(r[family].confidence_high)}` : "Range unavailable"}</small>{i > 0 && <small>Change: {formatAmount(r[family]?.yield_qph - compared[0][family]?.yield_qph)}</small>}</td>)}</tr>)}{Object.keys(units).map(key => <tr key={key}><th>{key} {units[key]}</th>{compared.map(r => <td key={r.id}>{r.inputs[key]}</td>)}</tr>)}</tbody></table></div></>}</section>}
    {harvestResult && <section className="feature-card" id="harvest-record"><h2>Actual harvest · {harvestResult.context?.fieldName || harvestResult.crop_type}</h2><p className="feature-help">Use harvested area and total harvested quantity. These records are not automatically used for training. A retrospective comparison is not a prospective accuracy test.</p><form className="feature-form" onSubmit={saveHarvest}><div className="feature-two"><label>Harvested quantity<input required type="number" min="0" max="1000000000000" step="any" value={quantity} onChange={e => setQuantity(e.target.value)} /></label><label>Quantity unit<select value={unit} onChange={e => setUnit(e.target.value)}><option value="kg">Kilograms</option><option value="q">Quintals</option><option value="t">Tonnes</option></select></label></div><div className="feature-two"><label>Harvested area<input required type="number" min="0.0001" max="1000000" step="any" value={area} onChange={e => setArea(e.target.value)} /></label><label>Area unit<select value={areaUnit} onChange={e => setAreaUnit(e.target.value)}><option value="ha">Hectares</option><option value="acre">Acres</option></select></label></div><label>Harvest date<input required type="date" max={new Date().toISOString().slice(0,10)} value={date} onChange={e => setDate(e.target.value)} /></label><label>Measurement notes / record reference<textarea maxLength={1000} value={note} onChange={e => setNote(e.target.value)} /></label><button type="submit" className="btn-primary">Save harvest record</button></form></section>}
    <section className="feature-card"><h2>Recorded outcomes</h2>{!store.harvests.length ? <p className="feature-empty">Choose Record actual harvest on a saved analysis to get started.</p> : <div className="feature-table-scroll"><table><thead><tr><th>Field / date</th><th>Observed q/ha</th><th>Estimated q/ha</th><th>Absolute error q/ha</th><th>Within reported interval?</th></tr></thead><tbody>{store.harvests.map(h => { const r = store.history.find(row => row.id === h.analysis_id); if (!r) return null; const p = r.recommended; return <tr key={h.id}><th>{r.context?.fieldName || r.crop_type}<small>{h.date}{h.date <= r.created_at.slice(0,10) ? " · Same-day or retrospective" : ""}</small></th><td>{formatAmount(h.actual_q_ha)}</td><td>{formatAmount(p.yield_qph)}</td><td>{formatAmount(Math.abs(p.yield_qph-h.actual_q_ha))}</td><td>{Number.isFinite(p.confidence_low) ? (h.actual_q_ha >= p.confidence_low && h.actual_q_ha <= p.confidence_high ? "Yes" : "No") : "Unavailable"}</td></tr>; })}</tbody></table></div>}<p className="feature-help">Observed yields are user-reported. Record matching crop, field and growing period; investigate differences before using them to assess model quality.</p></section>
  </main>;
}
