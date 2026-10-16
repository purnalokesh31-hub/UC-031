export const ACRES_PER_HECTARE = 2.471053814671653;

export function formatAmount(value, digits = 2) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
  const scale = 10 ** digits;
  return (Math.round((value + Number.EPSILON * Math.abs(value)) * scale) / scale).toFixed(digits);
}

export function formatYield(value, unit = "t") {
  if (typeof value !== "number" || !Number.isFinite(value)) return "Unavailable";
  return formatAmount(unit === "t" ? value / 10 : value);
}

export function harvestForArea(prediction, area, areaUnit, outsideRange = false) {
  const size = Number(area);
  if (outsideRange || area === "" || !Number.isFinite(size) || size <= 0 || size > 1000000 || !["ha", "acre"].includes(areaUnit)) return null;
  const point = prediction?.yield_qph;
  if (typeof point !== "number" || !Number.isFinite(point) || point <= 0) return null;
  const hectares = areaUnit === "acre" ? size / ACRES_PER_HECTARE : size;
  const factor = hectares / 10;
  const low = prediction.confidence_low;
  const high = prediction.confidence_high;
  const hasInterval = Number.isFinite(low) && Number.isFinite(high) && low >= 0 && high >= low;
  return { tonnes: point * factor, low: hasInterval ? low * factor : null, high: hasInterval ? high * factor : null };
}

export function intervalScale(predictions) {
  const values = predictions.flatMap(p => [p?.confidence_low, p?.confidence_high, p?.yield_qph]).filter(Number.isFinite);
  if (!values.length) return null;
  const min = Math.min(...values), max = Math.max(...values);
  const padding = Math.max((max - min) * 0.15, 0.1);
  return { min: min - padding, max: max + padding, position: value => (value - min + padding) / (max - min + 2 * padding) * 100 };
}
