import { useEffect, useRef, useState } from "react";
import { useWorkspace } from "../lib/WorkspaceStore";
import { ArrowRight, Check, CloudSun, Info, Layers, RotateCcw, Sprout, Loader, Sliders, Hash, Sparkles, Droplets, Sun, Bookmark, X, Calendar } from "lucide-react";

const CROPS = [
  { name: "Rice", icon: "🌾", baseline: "35–55 q/ha" },
  { name: "Wheat", icon: "🌾", baseline: "25–48 q/ha" },
  { name: "Maize", icon: "🌽", baseline: "30–60 q/ha" },
  { name: "Cotton", icon: "☁️", baseline: "12–25 q/ha" },
  { name: "Sugarcane", icon: "🎋", baseline: "550–850 q/ha" },
  { name: "Groundnut", icon: "🥜", baseline: "15–30 q/ha" },
];

const FIELDS = [
  { key: "N", label: "Nitrogen", symbol: "N", unit: "kg/ha", min: 0, max: 300, step: 1 },
  { key: "P", label: "Phosphorus", symbol: "P", unit: "kg/ha", min: 0, max: 150, step: 1 },
  { key: "K", label: "Potassium", symbol: "K", unit: "kg/ha", min: 0, max: 200, step: 1 },
  { key: "pH", label: "Soil pH", symbol: "pH", unit: "", min: 3, max: 10, step: 0.1 },
  { key: "moisture", label: "Soil moisture", symbol: "H₂O", unit: "%", min: 0, max: 100, step: 1 },
  { key: "temperature", label: "Temperature", symbol: "°C", unit: "°C", min: 5, max: 50, step: 0.5 },
  { key: "humidity", label: "Humidity", symbol: "RH", unit: "%", min: 0, max: 100, step: 1 },
  { key: "rainfall", label: "Rainfall", symbol: "☂", unit: "mm", min: 0, max: 500, step: 5 },
];

function cropDefaults(crop, allMetrics) {
  const bounds = allMetrics?.[crop]?.bounds;
  return Object.fromEntries(FIELDS.map(field => {
    const limits = bounds?.[field.key];
    const value = limits ? (limits[0] + limits[1]) / 2 : (field.min + field.max) / 2;
    const snapped = field.min + Math.round((value - field.min) / field.step) * field.step;
    return [field.key, Number(Math.min(limits?.[1] ?? field.max, Math.max(limits?.[0] ?? field.min, snapped)).toFixed(2))];
  }));
}

export default function InputForm({ onSubmit, isLoading, allMetrics, onCropChange, onValuesChange, editRequest, submitError }) {
  const { store, update, restoreRequest, online, storageError } = useWorkspace();
  const initial = useRef(store.draft);
  const [crop, setCrop] = useState(initial.current?.crop || "Rice");
  const [sources, setSources] = useState(initial.current?.sources || {});
  const [context, setContext] = useState(initial.current?.context || {});
  const [saveNote, setSaveNote] = useState("");
  const [values, setValues] = useState(() => initial.current?.values || cropDefaults(initial.current?.crop || "Rice", allMetrics));
  const [showSliders, setShowSliders] = useState(true); // Default to True for Sliding Style!
  const [fieldError, setFieldError] = useState(null);
  const [resetBackup, setResetBackup] = useState(null);
  const [pendingCrop, setPendingCrop] = useState(null);
  const [fieldsDrawerOpen, setFieldsDrawerOpen] = useState(false);
  const [provenanceDrawerOpen, setProvenanceDrawerOpen] = useState(false);

  useEffect(() => {
    if (editRequest) {
      document.getElementById("num-N")?.focus({ preventScroll: true });
      document.getElementById("field-form")?.scrollIntoView({ behavior: "instant", block: "start" });
    }
  }, [editRequest]);

  useEffect(() => {
    if (submitError) requestAnimationFrame(() => document.getElementById("analysis-error")?.focus());
  }, [submitError]);

  const sampleCount = FIELDS.filter(field => !sources[field.key]?.type || sources[field.key].type === "sample").length;
  const dirty = useRef(new Set(Object.keys(initial.current?.values || {})));
  const initializedCrop = useRef(initial.current?.values ? (initial.current.crop || "Rice") : allMetrics?.Rice?.bounds ? "Rice" : null);
  const cropMetrics = allMetrics?.[crop];

  const outsideCount = FIELDS.filter(({ key }) => {
    const range = cropMetrics?.bounds?.[key];
    return range && values[key] !== "" && (Number(values[key]) < range[0] || Number(values[key]) > range[1]);
  }).length;

  const groups = [
    { title: "Soil & Nutrients", icon: Layers, fields: FIELDS.slice(0, 4) },
    { title: "Weather & Climate", icon: CloudSun, fields: FIELDS.slice(4) },
  ];

  useEffect(() => {
    if (!restoreRequest) return;
    const draft = restoreRequest.draft;
    const next = draft.crop || "Rice";
    setCrop(next);
    setValues(draft.values || cropDefaults(next, allMetrics));
    setSources(draft.sources || {});
    setContext(draft.context || {});
    dirty.current = new Set(Object.keys(draft.values || {}));
    initializedCrop.current = draft.values || allMetrics?.[next]?.bounds ? next : null;
    setFieldError(null);
    setSaveNote("");
    setResetBackup(null);
    onCropChange?.(next);
    onValuesChange?.();
    setPendingCrop(null);
  }, [restoreRequest]);

  useEffect(() => {
    update(() => ({ draft: { crop, values, sources, context } }));
  }, [crop, values, sources, context, update]);

  function saveMeasurements() {
    update(current => ({
      fields: current.fields.map(field =>
        field.id === context.fieldId
          ? { ...field, scenario: { crop, values, sources }, updated_at: new Date().toISOString() }
          : field
      ),
    }));
    setSaveNote("Measurement scenario saved to this field.");
  }

  useEffect(() => {
    if (allMetrics?.[crop]?.bounds && initializedCrop.current !== crop) {
      initializedCrop.current = crop;
      setValues(current => {
        const trainedDefaults = cropDefaults(crop, allMetrics);
        return Object.fromEntries(
          FIELDS.map(field => [
            field.key,
            dirty.current.has(field.key) ? current[field.key] : trainedDefaults[field.key],
          ])
        );
      });
      onValuesChange?.();
    }
  }, [allMetrics, crop]);

  function chooseCrop(nextCrop) {
    if (nextCrop === crop) return;
    if (FIELDS.some(field => sources[field.key]?.type && sources[field.key].type !== "sample")) {
      setPendingCrop(nextCrop);
      return;
    }
    applyCrop(nextCrop, false);
  }

  function applyCrop(nextCrop, keepEntries) {
    setPendingCrop(null);
    setResetBackup(null);
    setSaveNote("");
    setCrop(nextCrop);
    if (!keepEntries) setSources({});
    setFieldError(null);
    if (!keepEntries) dirty.current.clear();
    initializedCrop.current = allMetrics?.[nextCrop]?.bounds ? nextCrop : null;
    const defaults = cropDefaults(nextCrop, allMetrics);
    setValues(current =>
      Object.fromEntries(
        FIELDS.map(field => [
          field.key,
          keepEntries && sources[field.key]?.type && sources[field.key].type !== "sample"
            ? current[field.key]
            : defaults[field.key],
        ])
      )
    );
    onCropChange?.(nextCrop);
    requestAnimationFrame(() => document.querySelector('input[name="crop"]:checked')?.focus());
  }

  function updateValue(key, rawValue) {
    setResetBackup(null);
    setSaveNote("");
    setFieldError(null);
    dirty.current.add(key);
    setSources(current => ({ ...current, [key]: { type: "user-entered", date: "" } }));
    setValues(current => ({ ...current, [key]: rawValue }));
    onValuesChange?.();
  }

  function applyPresetScenario(type) {
    setResetBackup({ values, sources, dirty: [...dirty.current] });
    setSaveNote("");
    const defaults = cropDefaults(crop, allMetrics);
    const bounds = cropMetrics?.bounds;
    const nextValues = { ...defaults };

    if (type === "optimal") {
      // defaults are already middle of bounds
    } else if (type === "monsoon") {
      if (bounds?.rainfall) nextValues.rainfall = Math.round(bounds.rainfall[1] * 0.95);
      if (bounds?.moisture) nextValues.moisture = Math.round(bounds.moisture[1] * 0.9);
      if (bounds?.humidity) nextValues.humidity = Math.min(95, Math.round((bounds.humidity[1] || 80) * 0.95));
    } else if (type === "drought") {
      if (bounds?.rainfall) nextValues.rainfall = Math.max(10, Math.round(bounds.rainfall[0] * 1.05));
      if (bounds?.moisture) nextValues.moisture = Math.max(15, Math.round(bounds.moisture[0] * 1.05));
      if (bounds?.temperature) nextValues.temperature = Math.min(45, Math.round((bounds.temperature[1] || 35) * 0.98));
    } else if (type === "nutrients") {
      if (bounds?.N) nextValues.N = Math.round(bounds.N[1] * 0.9);
      if (bounds?.P) nextValues.P = Math.round(bounds.P[1] * 0.9);
      if (bounds?.K) nextValues.K = Math.round(bounds.K[1] * 0.9);
    }

    setValues(nextValues);
    Object.keys(nextValues).forEach(k => dirty.current.add(k));
    onValuesChange?.();
  }

  function reset() {
    setResetBackup({ values, sources, dirty: [...dirty.current] });
    setSaveNote("");
    setSources({});
    setFieldError(null);
    dirty.current.clear();
    initializedCrop.current = allMetrics?.[crop]?.bounds ? crop : null;
    setValues(cropDefaults(crop, allMetrics));
    onValuesChange?.();
  }

  function undoReset() {
    if (!resetBackup) return;
    setValues(resetBackup.values);
    setSources(resetBackup.sources);
    dirty.current = new Set(resetBackup.dirty);
    setResetBackup(null);
    setFieldError(null);
    onValuesChange?.();
  }

  function validate(fields) {
    const invalid = fields.find(
      field =>
        values[field.key] === "" ||
        !Number.isFinite(Number(values[field.key])) ||
        Number(values[field.key]) < field.min ||
        Number(values[field.key]) > field.max
    );
    if (invalid) {
      setFieldError({
        key: invalid.key,
        message: `Enter ${invalid.label.toLowerCase()} between ${invalid.min} and ${invalid.max}${
          invalid.unit ? ` ${invalid.unit}` : ""
        }.`,
      });
      requestAnimationFrame(() => document.getElementById(`num-${invalid.key}`)?.focus());
      return false;
    }
    setFieldError(null);
    return true;
  }

  function submit(event) {
    event.preventDefault();
    if (pendingCrop || isLoading) return;
    if (!validate(FIELDS)) return;
    const today = new Date().toLocaleDateString("en-CA");
    const invalidSource = FIELDS.find(field => {
      const source = sources[field.key];
      return (source?.type === "measured" && !source.date) || (source?.date && source.date > today);
    });
    if (invalidSource) {
      setFieldError({ message: `Enter a measurement date on or before today for ${invalidSource.label}.` });
      setProvenanceDrawerOpen(true);
      requestAnimationFrame(() => document.getElementById(`source-date-${invalidSource.key}`)?.focus());
      return;
    }
    onSubmit(
      {
        ...Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)])),
        crop_type: crop,
      },
      {
        ...context,
        sources: Object.fromEntries(
          FIELDS.map(field => [field.key, sources[field.key] || { type: "sample", date: "" }])
        ),
      }
    );
  }

  return (
    <>
      <form id="field-form" onSubmit={submit} className="card input-panel direct-form" noValidate aria-busy={isLoading}>
        {/* Panel Heading */}
        <div className="input-panel-heading">
          <div className="input-heading-icon"><Sprout size={22} /></div>
          <div>
            <h2>Crop & Field Conditions</h2>
            <p>Slide parameters into range or fine-tune numbers to simulate yield.</p>
          </div>
          <span className="form-sample-label">
            {sampleCount === FIELDS.length ? "✨ Sample Ready" : sampleCount ? "🔄 Mixed Data" : "👤 Your Field Data"}
          </span>
        </div>

        <div className="input-panel-body">
          {/* Crop Carousel / Sliding Pills */}
          <fieldset className="crop-choice-group">
            <legend>Select Crop Variety</legend>
            <div className="crop-sliding-track" role="radiogroup" aria-label="Crop type">
              {CROPS.map(({ name, icon, baseline }, index) => {
                const isSelected = crop === name;
                return (
                  <label
                    key={name}
                    className={`crop-sliding-pill${isSelected ? " selected" : ""}`}
                    onClick={() => chooseCrop(name)}
                  >
                    <input
                      id={index === 0 ? "crop-select" : `crop-${name.toLowerCase()}`}
                      type="radio"
                      name="crop"
                      value={name}
                      checked={isSelected}
                      onChange={() => chooseCrop(name)}
                      disabled={isLoading}
                      className="sr-only"
                    />
                    <span className="crop-icon" aria-hidden="true">{icon}</span>
                    <span className="crop-name">{name}</span>
                    {isSelected ? (
                      <Check size={14} className="crop-check" />
                    ) : (
                      <small className="crop-baseline-tag">{baseline}</small>
                    )}
                  </label>
                );
              })}
            </div>
          </fieldset>

          {/* Pending crop warning dialog */}
          {pendingCrop && (
            <div className="crop-change-choice" role="status">
              <strong>Switch to {pendingCrop}?</strong>
              <p>Choose how to handle your current custom measurements.</p>
              <div>
                <button type="button" onClick={() => applyCrop(pendingCrop, true)}>Keep My Entries</button>
                <button type="button" onClick={() => applyCrop(pendingCrop, false)}>Load {pendingCrop} Defaults</button>
                <button
                  type="button"
                  onClick={() => {
                    setPendingCrop(null);
                    requestAnimationFrame(() => document.querySelector('input[name="crop"]:checked')?.focus());
                  }}
                >
                  Cancel
                </button>
              </div>
            </div>
          )}

          {/* Quick Scenario Slider Bar */}
          <div className="scenario-slider-bar">
            <span className="scenario-bar-title"><Sparkles size={14} /> Quick Scenarios:</span>
            <div className="scenario-chips">
              <button
                type="button"
                className="scenario-chip"
                onClick={() => applyPresetScenario("optimal")}
                disabled={isLoading}
                title="Reset to model calibrated optimal zone"
              >
                🌟 Balanced Optimal
              </button>
              <button
                type="button"
                className="scenario-chip"
                onClick={() => applyPresetScenario("monsoon")}
                disabled={isLoading}
                title="Simulate high monsoon rainfall and humidity"
              >
                <Droplets size={13} /> Monsoon Rain
              </button>
              <button
                type="button"
                className="scenario-chip"
                onClick={() => applyPresetScenario("drought")}
                disabled={isLoading}
                title="Simulate dry summer drought conditions"
              >
                <Sun size={13} /> Summer Drought
              </button>
              <button
                type="button"
                className="scenario-chip"
                onClick={() => applyPresetScenario("nutrients")}
                disabled={isLoading}
                title="Simulate high fertilizer nutrition"
              >
                🌱 High N-P-K
              </button>
            </div>
          </div>

          {/* Style Controls Header & Sliding Mode Toggle */}
          <div className="input-tools">
            <span className="input-tools-label">Field Parameters</span>
            <div className="sliding-segmented" role="group" aria-label="Input style">
              <button
                type="button"
                className={`sliding-segmented-btn${showSliders ? " active" : ""}`}
                aria-pressed={showSliders}
                onClick={() => setShowSliders(true)}
              >
                <Sliders size={14} />
                <span>Sliding Style</span>
              </button>
              <button
                type="button"
                className={`sliding-segmented-btn${!showSliders ? " active" : ""}`}
                aria-pressed={!showSliders}
                onClick={() => setShowSliders(false)}
              >
                <Hash size={14} />
                <span>Compact Numbers</span>
              </button>
            </div>
          </div>

          {/* Parameter Groups with Interactive Sliders */}
          <div className="parameter-groups">
            {groups.map((group, index) => (
              <section className="parameter-group" aria-labelledby={`condition-heading-${index}`} key={group.title}>
                <h3 className="condition-group-heading" id={`condition-heading-${index}`}>
                  <group.icon size={18} />
                  <span>{group.title}</span>
                </h3>
                <div className="parameter-grid">
                  {group.fields.map(field => (
                    <ParameterField
                      key={field.key}
                      field={field}
                      value={values[field.key]}
                      observedRange={cropMetrics?.bounds?.[field.key]}
                      disabled={isLoading}
                      invalid={fieldError?.key === field.key}
                      errorMessage={fieldError?.key === field.key ? fieldError.message : null}
                      showSlider={showSliders}
                      isSample={!sources[field.key]?.type || sources[field.key]?.type === "sample"}
                      onChange={updateValue}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>

          {fieldError && !fieldError.key && <p id="field-error" className="field-error" role="alert">{fieldError.message}</p>}
          {outsideCount > 0 && (
            <p className="training-range-note input-range-alert">
              <Info size={15} />
              <span>{outsideCount} {outsideCount === 1 ? "value is" : "values are"} outside training bounds. Prediction intervals will be withheld.</span>
            </p>
          )}

          {/* Slide-out Drawers Trigger Bar */}
          <div className="drawer-triggers-bar">
            <button
              type="button"
              className="drawer-trigger-btn"
              onClick={() => setFieldsDrawerOpen(true)}
            >
              <Bookmark size={15} />
              <span>{context.fieldName ? `Linked Field: ${context.fieldName}` : "Link a Saved Field…"}</span>
            </button>

            <button
              type="button"
              className="drawer-trigger-btn"
              onClick={() => setProvenanceDrawerOpen(true)}
            >
              <Calendar size={15} />
              <span>Measurement Dates & Lab Sources…</span>
            </button>
          </div>

          {submitError && (
            <p id="analysis-error" tabIndex={-1} className="field-error analysis-submit-error" role="alert">
              {submitError} Your inputs are kept; select Estimate yield to try again.
            </p>
          )}

          {/* Primary Action Button */}
          <div className="estimate-actions">
            <div>
              <strong>{crop}{context.fieldName ? ` · ${context.fieldName}` : ""}</strong>
              <span>{sampleCount ? `${sampleCount} sample ${sampleCount === 1 ? "value" : "values"}` : "Your entered measurements"}</span>
            </div>
            <button
              type="submit"
              disabled={isLoading || !cropMetrics || !online || !!pendingCrop}
              className="btn-primary"
              id="predict-btn"
            >
              {isLoading ? (
                <><Loader size={17} className="spin" /> Estimating Yield…</>
              ) : !online ? (
                "Reconnect to estimate"
              ) : !cropMetrics ? (
                "Loading models…"
              ) : (
                <>Estimate Yield <ArrowRight size={17} /></>
              )}
            </button>
          </div>

          {/* Secondary Draft Reset Actions */}
          <div className="scenario-secondary-actions">
            <span>{storageError ? "Export a backup to preserve your draft." : "Draft is synced locally."}</span>
            <button type="button" disabled={isLoading} onClick={reset} className="btn-ghost input-reset">
              <RotateCcw size={14} /> Reset to Samples
            </button>
          </div>

          {resetBackup && (
            <p className="reset-feedback" role="status">
              Sample values restored. <button type="button" disabled={isLoading} onClick={undoReset}>Undo reset</button>
            </p>
          )}

          {context.fieldId && (
            <div className="save-field-box">
              <button className="btn-ghost" type="button" disabled={isLoading} onClick={saveMeasurements}>
                Save Measurements to Field
              </button>
              {saveNote && <p role="status" className="feature-help">{saveNote}</p>}
            </div>
          )}
        </div>
      </form>

      {/* Slide-Over Drawer: Saved Fields */}
      {fieldsDrawerOpen && (
        <div className="slide-drawer-backdrop" onClick={() => setFieldsDrawerOpen(false)}>
          <div className="slide-drawer-panel" onClick={e => e.stopPropagation()}>
            <div className="slide-drawer-header">
              <h3><Bookmark size={20} /> Link a Saved Field</h3>
              <button type="button" className="slide-drawer-close" onClick={() => setFieldsDrawerOpen(false)} aria-label="Close drawer">
                <X size={18} />
              </button>
            </div>
            <div className="slide-drawer-body">
              <p className="text-sm text-gray-600">
                Link this yield scenario directly to one of your farm parcels to keep records organized.
              </p>
              <div className="field-drawer-list">
                <button
                  type="button"
                  className={`field-drawer-card${!context.fieldId ? " active" : ""}`}
                  onClick={() => {
                    setContext({});
                    onValuesChange?.();
                    setFieldsDrawerOpen(false);
                  }}
                >
                  <strong>No Linked Field</strong>
                  <small>Use standalone ad-hoc scenario</small>
                </button>

                {store.fields.filter(f => !f.archived || f.id === context.fieldId).map(f => (
                  <button
                    key={f.id}
                    type="button"
                    className={`field-drawer-card${context.fieldId === f.id ? " active" : ""}`}
                    onClick={() => {
                      setResetBackup(null);
                      setSaveNote("");
                      setPendingCrop(null);
                      setContext({
                        fieldId: f.id,
                        fieldName: f.name,
                        area: f.area,
                        areaUnit: f.areaUnit,
                        location: f.location,
                        latitude: f.latitude,
                        longitude: f.longitude,
                        start: f.start,
                        end: f.end,
                        weather: f.weather,
                      });
                      if (f.scenario) {
                        setCrop(f.scenario.crop);
                        setValues(f.scenario.values);
                        setSources(f.scenario.sources || {});
                        dirty.current = new Set(Object.keys(f.scenario.values));
                        initializedCrop.current = f.scenario.crop;
                        onCropChange?.(f.scenario.crop);
                      }
                      onValuesChange?.();
                      setFieldsDrawerOpen(false);
                    }}
                  >
                    <div className="field-card-top">
                      <strong>{f.name}</strong>
                      <span className="field-area-badge">{f.area} {f.areaUnit === "acre" ? "acres" : "ha"}</span>
                    </div>
                    {f.location && <small>{f.location}</small>}
                    {f.scenario && <small className="text-emerald-700">Has saved scenario: {f.scenario.crop}</small>}
                  </button>
                ))}
              </div>
              <div className="mt-4">
                <a href="#fields" onClick={() => setFieldsDrawerOpen(false)} className="btn-ghost w-full justify-center">
                  Manage Fields in Notebook →
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Slide-Over Drawer: Provenance & Dates */}
      {provenanceDrawerOpen && (
        <div className="slide-drawer-backdrop" onClick={() => setProvenanceDrawerOpen(false)}>
          <div className="slide-drawer-panel" onClick={e => e.stopPropagation()}>
            <div className="slide-drawer-header">
              <h3><Calendar size={20} /> Data Provenance & Lab Records</h3>
              <button type="button" className="slide-drawer-close" onClick={() => setProvenanceDrawerOpen(false)} aria-label="Close drawer">
                <X size={18} />
              </button>
            </div>
            <div className="slide-drawer-body">
              <p className="text-sm text-gray-600">
                Record whether each value is a generated sample, personal entry, or certified lab measurement.
              </p>
              <div className="provenance-fields-list">
                {FIELDS.map(field => (
                  <div className="provenance-item-card" key={field.key}>
                    <strong>{field.label} ({field.symbol})</strong>
                    <div className="provenance-row">
                      <label>
                        <span>Data Source</span>
                        <select
                          disabled={isLoading}
                          aria-label={`${field.label} source`}
                          value={sources[field.key]?.type || "sample"}
                          onChange={e => {
                            setResetBackup(null);
                            setSaveNote("");
                            setSources(current => ({
                              ...current,
                              [field.key]: { ...current[field.key], type: e.target.value },
                            }));
                            onValuesChange?.();
                          }}
                        >
                          <option value="sample">Sample default</option>
                          <option value="user-entered">User-entered</option>
                          <option value="measured">Measured / lab record</option>
                        </select>
                      </label>
                      <label>
                        <span>Measurement Date</span>
                        <input
                          disabled={isLoading}
                          id={`source-date-${field.key}`}
                          type="date"
                          aria-label={`${field.label} measurement date`}
                          value={sources[field.key]?.date || ""}
                          max={new Date().toLocaleDateString("en-CA")}
                          onChange={e => {
                            setResetBackup(null);
                            setSaveNote("");
                            setSources(current => ({
                              ...current,
                              [field.key]: {
                                type: current[field.key]?.type || "sample",
                                ...current[field.key],
                                date: e.target.value,
                              },
                            }));
                            onValuesChange?.();
                          }}
                        />
                      </label>
                    </div>
                  </div>
                ))}
              </div>
              <button
                type="button"
                className="btn-primary mt-4 w-full"
                onClick={() => setProvenanceDrawerOpen(false)}
              >
                Apply Provenance Records
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

function ParameterField({ field, value, observedRange, disabled, invalid, errorMessage, showSlider, onChange, isSample }) {
  const { key, label, symbol, unit, min, max, step } = field;
  const numeric = value === "" ? NaN : Number(value);
  const rangeValue = Number.isFinite(numeric) ? Math.min(max, Math.max(min, numeric)) : min;
  const progress = Math.max(0, Math.min(100, ((rangeValue - min) / (max - min)) * 100));
  const outsideRange = observedRange && Number.isFinite(numeric) && (numeric < observedRange[0] || numeric > observedRange[1]);

  // Sweet spot range positions on slider track
  const sweetSpotStart = observedRange ? Math.max(0, Math.min(100, ((observedRange[0] - min) / (max - min)) * 100)) : 0;
  const sweetSpotEnd = observedRange ? Math.max(0, Math.min(100, ((observedRange[1] - min) / (max - min)) * 100)) : 100;
  const sweetSpotWidth = sweetSpotEnd - sweetSpotStart;

  const observedLabel = observedRange
    ? `${observedRange[0].toFixed(step < 1 ? 1 : 0)}–${observedRange[1].toFixed(step < 1 ? 1 : 0)}${unit}`
    : "loading crop range";

  const handleStep = direction => {
    const currentNum = Number.isFinite(numeric) ? numeric : min;
    const delta = direction * (step < 1 ? 0.1 : 1);
    const nextVal = Math.min(max, Math.max(min, Number((currentNum + delta).toFixed(2))));
    onChange(key, nextVal);
  };

  const handleSnap = snapValue => {
    onChange(key, snapValue);
  };

  return (
    <div className={`parameter-field${outsideRange ? " is-outside" : ""}${invalid ? " is-invalid" : ""}`}>
      {/* Parameter Header */}
      <div className="parameter-field-top">
        <label htmlFor={`num-${key}`}>
          <span className="parameter-symbol">{symbol}</span>
          <span>{label}</span>
          <small className="input-origin">{isSample ? "Sample" : "Custom"}</small>
        </label>
        <div className="parameter-value-wrap">
          <input
            id={`num-${key}`}
            type="number"
            inputMode="decimal"
            min={min}
            max={max}
            step="any"
            value={value}
            required
            disabled={disabled}
            onChange={event => onChange(key, event.target.value)}
            aria-label={`${label} value`}
            aria-invalid={invalid || undefined}
            aria-describedby={invalid ? `hint-${key} error-${key}` : `hint-${key}`}
          />
          {unit && <span>{unit}</span>}
        </div>
      </div>

      {errorMessage && <p id={`error-${key}`} className="field-error inline-field-error" role="alert">{errorMessage}</p>}

      {/* Interactive Sliding Track & Controls */}
      {showSlider && (
        <div className="parameter-slider-wrapper">
          <div className="slider-stepper-wrap">
            <button
              type="button"
              className="slider-stepper-btn"
              onClick={() => handleStep(-1)}
              disabled={disabled || rangeValue <= min}
              aria-label={`Decrease ${label}`}
              title="Decrease"
            >
              −
            </button>

            <div className="slider-track-container">
              {/* Floating live bubble */}
              <div
                className="slider-floating-bubble"
                style={{ left: `${progress}%` }}
                aria-hidden="true"
              >
                {Number.isFinite(numeric) ? numeric : "—"} {unit}
              </div>

              {/* Visual Track */}
              <div className="slider-visual-track">
                {/* Sweet-Spot Band */}
                {observedRange && (
                  <div
                    className="slider-sweet-spot"
                    style={{ left: `${sweetSpotStart}%`, width: `${sweetSpotWidth}%` }}
                    title={`Model Coverage: ${observedLabel}`}
                  />
                )}
                {/* Filled Progress Gradient */}
                <div
                  className="slider-visual-progress"
                  style={{ width: `${progress}%` }}
                />
              </div>

              {/* Native Range Slider */}
              <input
                id={`rng-${key}`}
                className="parameter-slider-interactive"
                type="range"
                min={min}
                max={max}
                step={step}
                value={rangeValue}
                disabled={disabled}
                onChange={event => onChange(key, event.target.value)}
                aria-label={`Adjust ${label}`}
              />
            </div>

            <button
              type="button"
              className="slider-stepper-btn"
              onClick={() => handleStep(1)}
              disabled={disabled || rangeValue >= max}
              aria-label={`Increase ${label}`}
              title="Increase"
            >
              +
            </button>
          </div>

          {/* Preset Snap Chips */}
          <div className="slider-snap-chips">
            <button
              type="button"
              className="slider-snap-chip"
              onClick={() => handleSnap(min)}
              disabled={disabled}
            >
              Min {min}{unit}
            </button>
            {observedRange && (
              <button
                type="button"
                className="slider-snap-chip optimal-snap"
                onClick={() => handleSnap(Number(((observedRange[0] + observedRange[1]) / 2).toFixed(1)))}
                disabled={disabled}
                title="Snap to optimal midpoint"
              >
                Target {((observedRange[0] + observedRange[1]) / 2).toFixed(step < 1 ? 1 : 0)}{unit}
              </button>
            )}
            <button
              type="button"
              className="slider-snap-chip"
              onClick={() => handleSnap(max)}
              disabled={disabled}
            >
              Max {max}{unit}
            </button>
          </div>
        </div>
      )}

      {/* Field Footer & Status */}
      <div className="parameter-field-foot" id={`hint-${key}`}>
        <span className={outsideRange ? "range-warning" : "range-reference"}>
          {outsideRange ? `⚠️ Outside demo coverage (${observedLabel})` : `✨ In training coverage (${observedLabel})`}
        </span>
      </div>
    </div>
  );
}
