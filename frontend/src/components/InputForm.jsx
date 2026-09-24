import { useEffect, useRef, useState } from "react";
import { Activity, RotateCcw, Sprout, Loader } from "lucide-react";

const CROPS = ["Rice", "Wheat", "Maize", "Cotton", "Sugarcane", "Groundnut"];
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

export default function InputForm({ onSubmit, isLoading, allMetrics, onCropChange, onValuesChange }) {
  const [crop, setCrop] = useState("Rice");
  const [values, setValues] = useState(() => cropDefaults("Rice", allMetrics));
  const dirty = useRef(new Set());
  const initializedCrop = useRef(allMetrics?.Rice?.bounds ? "Rice" : null);
  const cropMetrics = allMetrics?.[crop];
  const groups = [
    { title: "Soil & nutrients", subtitle: "Field measurements", fields: FIELDS.slice(0, 4) },
    { title: "Weather & water", subtitle: "Growing conditions", fields: FIELDS.slice(4) },
  ];

  useEffect(() => {
    if (allMetrics?.[crop]?.bounds && initializedCrop.current !== crop) {
      initializedCrop.current = crop;
      setValues(current => {
      const trainedDefaults = cropDefaults(crop, allMetrics);
      return Object.fromEntries(FIELDS.map(field => [
        field.key,
        dirty.current.has(field.key) ? current[field.key] : trainedDefaults[field.key],
      ]));
      });
      onValuesChange?.();
    }
  }, [allMetrics, crop]);

  function chooseCrop(nextCrop) {
    setCrop(nextCrop);
    dirty.current.clear();
    initializedCrop.current = allMetrics?.[nextCrop]?.bounds ? nextCrop : null;
    setValues(cropDefaults(nextCrop, allMetrics));
    onCropChange?.(nextCrop);
  }

  function updateValue(key, rawValue) {
    dirty.current.add(key);
    setValues(current => ({ ...current, [key]: rawValue }));
    onValuesChange?.();
  }

  function reset() {
    dirty.current.clear();
    initializedCrop.current = allMetrics?.[crop]?.bounds ? crop : null;
    setValues(cropDefaults(crop, allMetrics));
    onValuesChange?.();
  }

  function submit(event) {
    event.preventDefault();
    onSubmit({ ...Object.fromEntries(Object.entries(values).map(([key, value]) => [key, Number(value)])), crop_type: crop });
  }

  return (
    <form id="field-form" onSubmit={submit} className="card input-panel"
      onInvalid={event => { const group = event.target.closest("details"); if (group) group.open = true; }}>
      <div className="input-panel-heading">
        <div className="input-heading-icon"><Sprout size={19} /></div>
        <div>
          <p className="input-eyebrow">01 / YOUR FIELD</p>
          <h2>Field conditions</h2>
          <p>Adjust the example values to match your field.</p>
        </div>
      </div>

      <div className="input-panel-body">
        <label className="input-crop-label" htmlFor="crop-select">Crop</label>
        <select id="crop-select" className="crop-select" value={crop} onChange={event => chooseCrop(event.target.value)} disabled={isLoading}>
          {CROPS.map(name => <option key={name} value={name}>{name}</option>)}
        </select>

        <div className="parameter-groups">
          {groups.map(group => (
            <details className="parameter-group" key={group.title} open>
              <summary className="parameter-group-heading">
                <div><h3>{group.title}</h3><p>{group.subtitle}</p></div>
                <span>{group.fields.length} inputs</span>
              </summary>
              <div className="parameter-grid">
                {group.fields.map(field => (
                  <ParameterField
                    key={field.key}
                    field={field}
                    value={values[field.key]}
                    observedRange={cropMetrics?.bounds?.[field.key]}
                    disabled={isLoading}
                    onChange={updateValue}
                  />
                ))}
              </div>
            </details>
          ))}
        </div>

        <p className="training-range-note"><Activity size={16} /> Demo ranges describe the training examples. Enter measured values for your scenario; these ranges are not recommended targets.</p>

        <div className="input-form-actions">
          <button type="submit" disabled={isLoading} className="btn-primary" id="predict-btn">
            {isLoading ? <><Loader size={16} className="spin" /> Calculating…</> : <>Estimate yield</>}
          </button>
          <button type="button" disabled={isLoading} onClick={reset} className="btn-ghost input-reset">
            <RotateCcw size={15} /> Use example values
          </button>
        </div>
      </div>
    </form>
  );
}

function ParameterField({ field, value, observedRange, disabled, onChange }) {
  const { key, label, symbol, unit, min, max, step } = field;
  const numeric = value === "" ? NaN : Number(value);
  const rangeValue = Number.isFinite(numeric) ? Math.min(max, Math.max(min, numeric)) : min;
  const progress = ((rangeValue - min) / (max - min)) * 100;
  const outsideRange = observedRange && Number.isFinite(numeric) && (numeric < observedRange[0] || numeric > observedRange[1]);
  const observedLabel = observedRange
    ? `${observedRange[0].toFixed(step < 1 ? 1 : 0)}–${observedRange[1].toFixed(step < 1 ? 1 : 0)}${unit}`
    : "loading crop range";

  return (
    <div className={`parameter-field${outsideRange ? " is-outside" : ""}`}>
      <div className="parameter-field-top">
        <label htmlFor={`num-${key}`}><span className="parameter-symbol">{symbol}</span>{label}</label>
        <div className="parameter-value-wrap">
          <input
            id={`num-${key}`} type="number" inputMode="decimal" min={min} max={max} step="any"
            value={value} required disabled={disabled} onChange={event => onChange(key, event.target.value)}
            aria-label={`${label} value`}
            aria-describedby={`hint-${key}`}
          />
          {unit && <span>{unit}</span>}
        </div>
      </div>
      <input
        id={`rng-${key}`} className="parameter-slider" type="range" min={min} max={max} step={step}
        value={rangeValue} disabled={disabled} style={{ "--range-progress": `${progress}%` }}
        onChange={event => onChange(key, event.target.value)} aria-label={`Adjust ${label}`}
      />
      <div className="parameter-field-foot" id={`hint-${key}`}>
        <span>{min}{unit} <i>to</i> {max}{unit}</span>
        <span className={outsideRange ? "range-warning" : "range-reference"}>
          {outsideRange ? "Outside demo range" : `Demo range ${observedLabel}`}
        </span>
      </div>
    </div>
  );
}
