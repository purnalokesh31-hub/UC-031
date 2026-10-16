import { useEffect, useRef, useState } from "react";
import { useWorkspace, newId } from "../lib/WorkspaceStore";
import { api } from "../api";

const blank = { name: "", location: "", area: "1", areaUnit: "ha", latitude: "", longitude: "", start: "", end: "" };
export default function FieldNotebook() {
  const { store, update, restore, online, location, requestLocation } = useWorkspace();
  const [field, setField] = useState(blank);
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [weather, setWeather] = useState(null);
  const [editing, setEditing] = useState(!store.fields.some(f => !f.archived));
  const [advanced, setAdvanced] = useState(false);
  const formRef = useRef(null);
  const useLocationWhenReady = useRef(false);
  const activeFields = store.fields.filter(f => !f.archived);
  const detected = location.status === "ready" ? location.coordinates : null;
  const locationAccuracy = location.accuracy != null ? `Approximate accuracy ${Math.round(location.accuracy)} m.` : "Accuracy unavailable.";
  const detectedValues = () => ({ latitude: detected.latitude.toFixed(6), longitude: detected.longitude.toFixed(6), coordinateSource: "device", coordinateAccuracyM: location.accuracy });
  useEffect(() => {
    if (!detected) return;
    const replace = useLocationWhenReady.current;
    useLocationWhenReady.current = false;
    if (replace) {
      setWeather(null);
      setAdvanced(true);
      setNotice("Detected coordinates added. Check that they match your field before saving.");
    }
    setField(current => {
      if (!replace && (current.id || current.latitude !== "" || current.longitude !== "")) return current;
      return { ...current, ...detectedValues() };
    });
  }, [detected, location.accuracy]);
  function applyDetectedLocation() {
    if (!detected) { useLocationWhenReady.current = true; requestLocation(); return; }
    setField(current => ({ ...current, ...detectedValues() }));
    setWeather(null); setAdvanced(true); setNotice("Detected coordinates added. Check that they match your field before saving.");
  }
  function openEditor(item = blank) {
    setField(item.id || !detected ? item : { ...item, ...detectedValues() });
    setWeather(item.weather || null); setNotice("");
    setAdvanced(Boolean(item.start || item.latitude)); setEditing(true);
    requestAnimationFrame(() => {
      formRef.current?.scrollIntoView({ block: "start", behavior: "instant" });
      document.getElementById("field-name")?.focus({ preventScroll: true });
    });
  }
  const set = (key, value) => { setField(current => ({ ...current, [key]: value, ...(["latitude", "longitude"].includes(key) ? { coordinateSource: "manual", coordinateAccuracyM: null } : {}) })); if (["latitude", "longitude", "start", "end"].includes(key)) setWeather(null); };
  function save(event) {
    event.preventDefault();
    if ((field.start || field.end) && (!field.start || !field.end || field.start > field.end)) { setAdvanced(true); setNotice("Choose both growing dates, with the end on or after the start."); return; }
    const existing = store.fields.find(f => f.id === field.id);
    const saved = { ...field, name: field.name.trim(), id: field.id || newId(), weather, scenario: existing?.scenario || null, updated_at: new Date().toISOString() };
    if (!saved.name) { setNotice("Enter a field name."); return; }
    update(current => ({ fields: [...current.fields.filter(f => f.id !== saved.id), saved] }));
    setField(saved); setNotice(`${saved.name} saved. You can now estimate its yield.`);
    if (event.nativeEvent.submitter?.value === "estimate") useField(saved);
    else setEditing(false);
  }
  function useField(item) {
    restore({ ...(item.scenario || { crop: "Rice", values: null, sources: {} }), context: { fieldId: item.id, fieldName: item.name, area: item.area, areaUnit: item.areaUnit, location: item.location, latitude: item.latitude, longitude: item.longitude, start: item.start, end: item.end, weather: item.weather } });
  }
  async function fetchWeather() {
    const useCurrent = field.latitude === "" && field.longitude === "" && Boolean(detected);
    const latitude = useCurrent ? detected.latitude : Number(field.latitude);
    const longitude = useCurrent ? detected.longitude : Number(field.longitude);
    const missingCoordinates = field.latitude === "" || field.longitude === "";
    if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
        (missingCoordinates && !useCurrent) || !field.start || !field.end) {
      setNotice("Add both growing dates and check the coordinates. If location was blocked, enter latitude and longitude manually."); return;
    }
    setBusy(true); setNotice(""); setWeather(null);
    try {
      const response = await api.post("/workspace/weather", { latitude, longitude, start: field.start, end: field.end }, { timeout: 40000 });
      if (useCurrent) setField(current => ({ ...current, ...detectedValues() }));
      setWeather(response.data); setNotice("Weather context loaded. Save the field to retain it.");
    } catch (error) { setNotice(typeof error.response?.data?.detail === "string" ? error.response.data.detail : "Could not import weather. Use valid coordinates and 1–366 historical days, ending before today."); }
    finally { setBusy(false); }
  }
  return <main className="page-content notebook-page">
    <header className="feature-page-heading fields-heading"><div><p className="dashboard-eyebrow">MY FIELDS</p><h1>Your fields, in one place.</h1><p>Choose a saved field to estimate its yield, or add a new one.</p></div><button type="button" className="btn-primary" disabled={busy} onClick={() => openEditor()}>+ Add a field</button></header>
    <section className="field-workflow" aria-label="How the analysis works"><div className="field-workflow-heading"><span>WORKFLOW</span><p>From field details to a yield estimate</p></div><ol><li><span>01</span><div><strong>Field details</strong><small>Name and area</small></div></li><li><span>02</span><div><strong>Crop conditions</strong><small>Review inputs</small></div></li><li><span>03</span><div><strong>Yield estimate</strong><small>Compare results</small></div></li></ol></section>
    {notice && !editing && <p role="status" className="feature-notice">{notice}</p>}
    <div className={`notebook-grid field-workspace${editing ? " is-editing" : ""}`}>
      {editing && <section className="feature-card field-editor" ref={formRef} aria-labelledby="field-editor-title"><h2 id="field-editor-title">{field.id ? "Edit field details" : "Add your field"}</h2><p className="field-form-intro">Start with a name and area. Everything else is optional.</p>
      <form onSubmit={save}><fieldset disabled={busy} className="feature-form feature-fieldset"><label htmlFor="field-name">Field name<input id="field-name" required maxLength={80} placeholder="e.g. East rice field" value={field.name} onChange={e => set("name", e.target.value)} /></label>
        <div className="feature-two"><label>Field area<input type="number" min="0.0001" max="1000000" step="any" required value={field.area} onChange={e => set("area", e.target.value)} /></label><label>Area unit<select value={field.areaUnit} onChange={e => set("areaUnit", e.target.value)}><option value="ha">Hectares</option><option value="acre">Acres</option></select></label></div>
        <label>Village or location <span className="optional-label">Optional</span><input maxLength={150} placeholder="e.g. Village name" value={field.location} onChange={e => set("location", e.target.value)} /></label>
        <details className="field-optional" open={advanced} onToggle={e => setAdvanced(e.currentTarget.open)}><summary>Growing dates & weather <span>{field.coordinateSource === "device" ? "Device coordinates added" : "Optional"}</span></summary><div className="feature-form">
        <div className="feature-two"><label>Growing period start<input type="date" value={field.start} onChange={e => set("start", e.target.value)} /></label><label>Growing period end<input type="date" value={field.end} onChange={e => set("end", e.target.value)} /></label></div>
        <div className="detected-location"><div><strong>{detected ? "Device location available" : location.status === "locating" ? "Finding your location…" : "Device location unavailable"}</strong><p>{detected ? `Coordinates are approximate. ${locationAccuracy} Confirm they match the field.` : location.status === "denied" ? "Allow location in your browser, or enter coordinates below." : "You can enter coordinates below."}</p></div><button type="button" className="btn-ghost" disabled={busy || location.status === "locating"} onClick={applyDetectedLocation}>{detected ? "Use current location" : "Try location again"}</button></div>
        <div className="feature-two"><label>Latitude (optional)<input type="number" min="-90" max="90" step="any" value={field.latitude} onChange={e => set("latitude", e.target.value)} /></label><label>Longitude (optional)<input type="number" min="-180" max="180" step="any" value={field.longitude} onChange={e => set("longitude", e.target.value)} /></label></div>
        <p className="feature-help">Coordinates are saved with this field when you select Save. Weather lookup sends them and the dates to NASA POWER only when you select Look up past weather. Weather does not change the yield estimate.</p>
        <button type="button" className="btn-ghost" disabled={busy || !online} onClick={fetchWeather}>{busy ? "Importing weather…" : "Look up past weather"}</button>
        {weather && <section className="weather-preview"><h3>NASA POWER · {weather.days} complete days</h3><dl><div><dt>Mean temperature</dt><dd>{weather.mean_temperature_c.toFixed(1)} °C</dd></div><div><dt>Total rainfall</dt><dd>{weather.rainfall_total_mm.toFixed(1)} mm</dd></div><div><dt>Mean humidity</dt><dd>{weather.mean_humidity_pct.toFixed(1)}%</dd></div></dl><p>{weather.start} to {weather.end} · UTC<br />Retrieved {new Date(weather.retrieved_at).toLocaleString()}</p><a href={weather.documentation_url} target="_blank" rel="noreferrer">Source and method</a></section>}
        </div></details>
        {notice && <p role="status" className="feature-notice">{notice}</p>}
        <div className="feature-actions field-save-actions"><button className="btn-primary" disabled={busy} type="submit" value="estimate">Save & estimate yield →</button><button className="btn-ghost" disabled={busy} type="submit" value="save">Save field only</button>{activeFields.length > 0 && <button className="btn-ghost" type="button" onClick={() => { setEditing(false); setNotice(""); }}>Cancel</button>}</div>
      </fieldset></form></section>}
      <section className="feature-card saved-fields"><div className="saved-fields-heading"><div><p>FIELD RECORDS</p><h2>Saved fields</h2></div><span className="count-label">{activeFields.length} {activeFields.length === 1 ? "field" : "fields"}</span></div>
        {!activeFields.length && <div className="field-empty"><h3>Your first field starts here</h3><p>Give it a name you recognise and add its area. You can fill in crop measurements in the next step.</p><p className="feature-help">Just exploring? Try the sample inputs first.</p><a href="#dashboard">Explore a sample estimate →</a></div>}
        {activeFields.map((item, index) => <article className="notebook-item field-listing" key={item.id}>
          <div className="field-listing-top"><span>FIELD {String(index + 1).padStart(2, "0")}</span><span>{item.scenario ? "Measurements saved" : "Ready for analysis"}</span></div>
          <h3>{item.name}</h3>
          <div className="field-facts"><div><span>LOCATION</span><strong>{item.location || "Not added"}</strong></div><div><span>AREA</span><strong>{item.area} {item.areaUnit === "ha" ? "hectares" : "acres"}</strong></div><div><span>GROWING PERIOD</span><strong>{item.start && item.end ? `${item.start} to ${item.end}` : "Add when available"}</strong></div></div>
          <div className="feature-actions"><button className="btn-primary" onClick={() => useField(item)}>Estimate yield →</button><button className="btn-ghost" disabled={busy} onClick={() => openEditor(item)}>Edit details</button><button className="btn-ghost field-archive" onClick={() => { update(current => ({ fields: current.fields.map(f => f.id === item.id ? { ...f, archived: true } : f) })); if (field.id === item.id) setEditing(false); setNotice(`${item.name} archived. You can restore it below.`); }}>Archive</button></div>
        </article>)}
        {!!store.fields.filter(f => f.archived).length && <details><summary>Archived fields</summary>{store.fields.filter(f => f.archived).map(item => <p key={item.id}>{item.name} <button className="btn-ghost" onClick={() => update(current => ({ fields: current.fields.map(f => f.id === item.id ? { ...f, archived: false } : f) }))}>Restore</button></p>)}</details>}
      </section></div>
  </main>;
}
