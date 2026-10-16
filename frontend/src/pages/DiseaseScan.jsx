import { useState, useRef, useCallback, useEffect } from "react";
import { api, isCancel } from "../api";
import "../disease.css";
import {
  Upload, Camera, Leaf, RotateCcw, CheckCircle, XCircle,
  AlertTriangle, TrendingUp, Clock, BarChart2, Microscope,
  ChevronDown, Info, Zap, RefreshCw, Database,
} from "lucide-react";

const API_BASE = ""; // uses shared api instance (baseURL set in api.js)

// The checked-in ONNX model produces 38 PlantVillage classes across these crops.
const SUPPORTED_CROPS = [
  "Apple", "Blueberry", "Cherry", "Corn", "Grape", "Orange", "Peach",
  "Bell Pepper", "Potato", "Raspberry", "Soybean", "Squash", "Strawberry", "Tomato",
];

// ── Confidence tier styles ──────────────────────────────────────────────── //
const TIER_STYLES = {
  high:      { color: "#627b4e", label: "High Confidence",           bg: "#f2f5ed", border: "#dce5d3" },
  medium:    { color: "#836746", label: "Medium Confidence",          bg: "#f8f6ee", border: "#e7dfc7" },
  uncertain: { color: "#956549", label: "Uncertain — Review Advised", bg: "#faf4ed", border: "#ead8c6" },
  rejected:  { color: "#9b6252", label: "Low Confidence",             bg: "#faf1ed", border: "#e8d1c7" },
};

// ── Radial confidence gauge ────────────────────────────────────────────── //
function ConfidenceGauge({ value = 0, tier = "medium" }) {
  const r = 42;
  const circ = 2 * Math.PI * r;
  const offset = circ - (circ * value) / 100;
  const style = TIER_STYLES[tier] || TIER_STYLES.medium;

  return (
    <div style={{ position: "relative", width: 100, height: 100, flexShrink: 0 }}>
      <svg width="100" height="100" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="50" cy="50" r={r} fill="none" stroke="#e5e7eb" strokeWidth="9" />
        <circle
          cx="50" cy="50" r={r} fill="none"
          stroke={style.color} strokeWidth="9" strokeLinecap="round"
          strokeDasharray={circ} strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1.2s ease-out" }}
        />
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex",
        flexDirection: "column", alignItems: "center", justifyContent: "center",
      }}>
        <span style={{ fontWeight: 800, fontSize: "1.1rem", color: style.color, lineHeight: 1 }}>
          {value}%
        </span>
        <span style={{ fontSize: "0.55rem", color: "#9ca3af", textTransform: "uppercase", marginTop: 2 }}>
          Conf.
        </span>
      </div>
    </div>
  );
}

// ── History item (premium card) ─────────────────────────────────────────── //
function HistoryItem({ scan, onClick }) {
  const healthy = scan.is_healthy;
  const tier    = scan.confidence_tier || "medium";
  const ts      = TIER_STYLES[tier] || TIER_STYLES.medium;

  return (
    <button type="button" className="history-item"
      onClick={() => onClick(scan)}
      aria-label={`View ${scan.english_name || scan.telugu_name || "unknown"} scan details`}
      style={{
        display: "flex", alignItems: "center", gap: 12,
        width: "100%", textAlign: "left", font: "inherit",
        padding: "11px 14px",
        borderRadius: 12,
        background: "#fff",
        border: "1px solid var(--border)",
        borderLeft: `3.5px solid ${healthy ? "var(--g400)" : ts.color}`,
        cursor: "pointer",
        marginBottom: 8,
        boxShadow: "var(--s-xs)",
        transition: "all 0.16s ease",
      }}
      onMouseEnter={e => {
        e.currentTarget.style.boxShadow = "var(--s-green-sm)";
        e.currentTarget.style.transform = "translateX(2px)";
        e.currentTarget.style.borderColor = healthy ? "var(--g300)" : ts.border;
      }}
      onMouseLeave={e => {
        e.currentTarget.style.boxShadow = "var(--s-xs)";
        e.currentTarget.style.transform = "translateX(0)";
        e.currentTarget.style.borderColor = "var(--border)";
      }}
    >
      {/* Icon */}
      <span style={{
        width: 36, height: 36, borderRadius: 10, flexShrink: 0,
        background: healthy ? "var(--g50)" : ts.bg,
        border: `1.5px solid ${healthy ? "var(--g200)" : ts.border}`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: "1.1rem",
      }}>
        {healthy ? <Leaf size={17} color="#71865f" strokeWidth={1.7} /> : <Microscope size={16} color={ts.color} strokeWidth={1.7} />}
      </span>

      {/* Text */}
      <span style={{ flex: 1, minWidth: 0, display: "block" }}>
        <span style={{
          display: "block",
          fontSize: "0.79rem", fontWeight: 700, color: "var(--text-900)",
          whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis",
          marginBottom: 2,
        }}>
          {scan.english_name || scan.telugu_name || "Unknown"}
        </span>
        <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
          <Clock size={10} color="var(--text-300)" />
          <span style={{ fontSize: "0.67rem", color: "var(--text-400)" }}>
            {new Date(scan.timestamp).toLocaleString("en-IN", {
              day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit",
            })}
          </span>
        </span>
      </span>

      {/* Confidence pill */}
      <span style={{
        fontSize: "0.71rem", fontWeight: 800, color: ts.color,
        background: ts.bg, border: `1.5px solid ${ts.border}`,
        padding: "3px 10px", borderRadius: 99,
        fontFamily: "'JetBrains Mono', monospace",
        letterSpacing: "-0.3px",
        flexShrink: 0,
      }}>
        {scan.confidence?.toFixed(0)}%
      </span>
    </button>
  );
}

// ═══════════════════════════════════════════════════════════════════════════ //
export default function DiseaseScan() {
  // Upload state
  const [dragging,   setDragging]   = useState(false);
  const [scanning,   setScanning]   = useState(false);
  const [previewURL, setPreviewURL] = useState(null);
  const [result,     setResult]     = useState(null);
  const [error,      setError]      = useState(null);
  const [splitPos,   setSplitPos]   = useState(50);

  // Feedback
  const [feedbackSent, setFeedbackSent] = useState(false);
  const [showCorrect,  setShowCorrect]  = useState(false);
  const [correcting,   setCorrecting]   = useState(false);
  const [feedbackError, setFeedbackError] = useState(null);

  // History + analytics
  const [history,    setHistory]    = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyError, setHistoryError] = useState(null);
  const [analytics,  setAnalytics]  = useState(null);
  const [analyticsError, setAnalyticsError] = useState(null);
  const [engineMode, setEngineMode] = useState(null);
  const [activeTab,  setActiveTab]  = useState("history"); // history | analytics

  // History detail modal
  const [detailScan, setDetailScan] = useState(null);

  useEffect(() => {
    if (!detailScan) return;
    const closeOnEscape = event => { if (event.key === "Escape") setDetailScan(null); };
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [detailScan]);

  const fileInputRef = useRef(null);
  const selectedFileRef = useRef(null);
  const scanController = useRef(null);
  const previewRef = useRef(null);
  useEffect(() => () => {
    scanController.current?.abort();
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
  }, []);

  // ── Load history + analytics + engine status on mount ──────────────── //
  const fetchHistory = useCallback(async (signal) => {
    setHistoryLoading(true);
    setHistoryError(null);
    try {
      const res = await api.get("/disease/history?limit=10", { signal, timeout: 5000 });
      setHistory(res.data.scans || []);
    } catch (e) {
      if (!isCancel(e)) setHistoryError(e.response?.data?.detail || "Could not refresh scan history.");
    } finally { if (!signal?.aborted) setHistoryLoading(false); }
  }, []);

  const fetchAnalytics = useCallback(async (signal) => {
    setAnalyticsError(null);
    try {
      const res = await api.get("/disease/analytics", { signal, timeout: 5000 });
      setAnalytics(res.data);
    } catch (e) {
      if (!isCancel(e)) setAnalyticsError(e.response?.data?.detail || "Could not load scan analytics.");
    }
  }, []);

  const fetchEngineStatus = useCallback(async (signal) => {
    try {
      const res = await api.get("/disease/engine-status", { signal, timeout: 5000 });
      setEngineMode(res.data);
    } catch (e) { if (!isCancel(e)) {/* silent */} }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const { signal } = controller;
    fetchHistory(signal);
    fetchAnalytics(signal);
    fetchEngineStatus(signal);
    return () => controller.abort();
  }, [fetchHistory, fetchAnalytics, fetchEngineStatus]);

  // ── Drag handlers ───────────────────────────────────────────────────── //
  const onDragOver  = useCallback(e => { e.preventDefault(); setDragging(true);  }, []);
  const onDragLeave = useCallback(()  => setDragging(false), []);

  // ── File processing ─────────────────────────────────────────────────── //
  const processFile = useCallback((file) => {
    if (!file.type.startsWith("image/")) {
      setError("Please upload a valid image file (JPG, PNG, WEBP).");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("Please upload an image under 10 MB.");
      return;
    }
    selectedFileRef.current = file;
    // Revoke previous blob URL to avoid memory leaks
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = URL.createObjectURL(file);
    setPreviewURL(previewRef.current);
    setResult(null);
    setError(null);
    setFeedbackSent(false);
    setFeedbackError(null);
    setShowCorrect(false);
    uploadAndAnalyze(file);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const onDrop = useCallback(e => {
    e.preventDefault(); setDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) processFile(file);
  }, [processFile]);

  const uploadAndAnalyze = async (file) => {
    scanController.current?.abort();
    setScanning(true);
    const controller = new AbortController();
    scanController.current = controller;
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await api.post("/disease/scan", fd, {
        timeout: 30000,
        signal:  controller.signal,
      });
      if (controller.signal.aborted) return;
      if (!res.data.success) {
        setError(res.data.error || "Analysis failed.");
      } else {
        setResult(res.data);
        fetchHistory();
        fetchAnalytics();
      }
    } catch (e) {
      if (!isCancel(e)) {
        setError(
          e.code === "ECONNABORTED"
            ? "Request timed out. Make sure the backend server is running."
            : e.response?.data?.detail || "Could not connect to server."
        );
      }
    } finally {
      if (scanController.current === controller) setScanning(false);
    }
  };

  const sendFeedback = async (type, correctedClass = null) => {
    if (!result?.scan_id) {
      setFeedbackError("This scan is not saved, so feedback cannot be attached to it.");
      return;
    }
    setCorrecting(true);
    setFeedbackError(null);
    try {
      await api.post("/disease/feedback", {
        scan_id:         result.scan_id,
        feedback:        type,
        corrected_class: correctedClass,
      });
      setFeedbackSent(true);
      setShowCorrect(false);
      fetchAnalytics();
    } catch (e) {
      setFeedbackError(e.response?.data?.detail || "Feedback could not be saved. Please try again.");
    }
    finally { setCorrecting(false); }
  };

  const submitCorrection = () => {
    const value = document.getElementById("correctClass")?.value?.trim();
    if (!value) {
      setFeedbackError("Enter the correct disease name before submitting.");
      document.getElementById("correctClass")?.focus();
      return;
    }
    sendFeedback("wrong", value);
  };

  const reset = () => {
    scanController.current?.abort();
    selectedFileRef.current = null;
    if (previewRef.current) URL.revokeObjectURL(previewRef.current);
    previewRef.current = null;
    setPreviewURL(null);
    setResult(null);
    setError(null);
    setScanning(false);
    setFeedbackSent(false);
    setFeedbackError(null);
    setShowCorrect(false);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const retryScan = () => {
    const file = selectedFileRef.current;
    if (!file) return reset();
    setError(null);
    setResult(null);
    setFeedbackError(null);
    uploadAndAnalyze(file);
  };

  // ── Tier badge ──────────────────────────────────────────────────────── //
  const tier      = result?.confidence_tier || "medium";
  const tierStyle = TIER_STYLES[tier] || TIER_STYLES.medium;

  // ── History item click handler ───────────────────────────────────────── //
  const handleHistoryClick = (scan) => setDetailScan(scan);

  // ══════════════════════════════════════════════════════════════════════ //
  //  RENDER                                                               //
  // ══════════════════════════════════════════════════════════════════════ //
  return (
    <div className="disease-layout" style={{ minHeight: "80vh", position: "relative" }}>

      <header className="scan-heading">
        <div><span className="dashboard-eyebrow"><Leaf size={15} /> LEAF INSIGHTS</span>
          <h1>A closer look at your crop.</h1>
          <p>Upload a clear leaf photograph to explore possible conditions and review your previous scans.</p>
        </div>
        {engineMode && <span className={`api-status ${engineMode.model_ready ? "api-status-online" : "api-status-offline"}`} role="status"><span className="api-status-dot" />{engineMode.model_ready ? "Ready to scan" : "Scanner unavailable"}</span>}
      </header>

      {/* ── HISTORY DETAIL MODAL ─────────────────────────────────────── */}
      {detailScan && (
        <div
          onClick={() => setDetailScan(null)}
          role="presentation"
          style={{
            position: "fixed", inset: 0, zIndex: 300,
            background: "rgba(15,23,42,0.4)", backdropFilter: "blur(4px)",
            display: "flex", alignItems: "center", justifyContent: "center",
            padding: 24,
          }}
        >
          <div
            onClick={e => e.stopPropagation()}
            className="card"
            role="dialog"
            aria-modal="true"
            aria-label={`${detailScan.english_name || "Scan"} details`}
            style={{ width: "100%", maxWidth: 420, padding: 0 }}
          >
            <div style={{
              background: detailScan.is_healthy ? "var(--g50)" : "var(--amb50)",
              borderBottom: "1px solid var(--border)",
              padding: "14px 18px",
              display: "flex", alignItems: "center", justifyContent: "space-between",
            }}>
              <div>
                <div style={{ fontWeight: 700, color: "var(--text-900)", fontSize: "0.95rem" }}>
                  {detailScan.english_name || "Unknown"}
                </div>
                {detailScan.telugu_name && detailScan.telugu_name !== "తెలియని వ్యాధి" && (
                  <div style={{ fontSize: "0.73rem", color: "var(--text-500)", marginTop: 2 }}>
                    {detailScan.telugu_name}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => setDetailScan(null)}
                aria-label="Close scan details"
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "var(--text-400)", fontSize: "1.3rem", lineHeight: 1,
                }}
              >×</button>
            </div>
            <div style={{ padding: "14px 18px", display: "flex", flexDirection: "column", gap: 10 }}>
              <span style={{ fontSize: "0.72rem", fontWeight: 600, display: "inline-block",
                background: (TIER_STYLES[detailScan.confidence_tier] || TIER_STYLES.medium).bg,
                color: (TIER_STYLES[detailScan.confidence_tier] || TIER_STYLES.medium).color,
                border: `1px solid ${(TIER_STYLES[detailScan.confidence_tier] || TIER_STYLES.medium).border}`,
                padding: "3px 10px", borderRadius: 20,
              }}>
                {detailScan.confidence?.toFixed(1)}% — {(TIER_STYLES[detailScan.confidence_tier] || TIER_STYLES.medium).label}
              </span>
              {detailScan.solution && detailScan.solution !== "పంట ఆరోగ్యాన్ని గమనిస్తూ ఉండండి." ? (
                <div style={{ background: "var(--g50)", border: "1px solid var(--g200)", borderRadius: 10, padding: 12 }}>
                  <div style={{ fontSize: "0.65rem", fontWeight: 600, color: "var(--text-500)", textTransform: "uppercase", marginBottom: 5 }}>Solution</div>
                  <p style={{ fontSize: "0.8rem", color: "var(--text-700)", margin: 0, lineHeight: 1.55 }}>{detailScan.solution}</p>
                </div>
              ) : !detailScan.is_healthy ? (
                <p style={{ fontSize: "0.8rem", color: "var(--text-600)", margin: 0, lineHeight: 1.55 }}>
                  No crop-specific treatment guidance is available for this scan. Confirm the diagnosis with a qualified local agronomist before treating the plant.
                </p>
              ) : null}
              <p style={{ fontSize: "0.68rem", color: "var(--text-400)", margin: 0 }}>
                Scanned: {new Date(detailScan.timestamp).toLocaleString("en-IN")}
              </p>
              <button type="button" onClick={() => setDetailScan(null)} className="btn-secondary" style={{ marginTop: 2 }}>Close</button>
            </div>
          </div>
        </div>
      )}

      {/* ── LEFT PANEL — Upload / Results ────────────────────────────── */}
        <div className="disease-upload-column" style={{ display: "flex", flexDirection: "column", gap: 16 }}>

        {/* Model Not Ready Banner */}
        {engineMode && !engineMode.model_ready && (
          <div style={{
            padding: "16px 18px", borderRadius: 14,
            background: "#fefce8", border: "1.5px solid #fde047",
          }}>
            <div style={{ display: "flex", gap: 10, alignItems: "flex-start" }}>
              <AlertTriangle size={18} color="#b45309" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                {engineMode.model_h5_exists && !engineMode.model_onnx_exists ? (
                  <>
                    <p style={{ fontSize: "0.82rem", fontWeight: 700, color: "#92400e", marginBottom: 6 }}>
                      Model downloaded — ONNX conversion required
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "#78350f", marginBottom: 10, lineHeight: 1.5 }}>
                      The H5 model is downloaded but Python 3.14 requires the ONNX format.
                      Convert it using Google Colab (free, ~2 minutes):
                    </p>
                    <code style={{
                      display: "block", fontSize: "0.72rem", fontFamily: "monospace",
                      background: "#fef3c7", padding: "8px 12px", borderRadius: 8,
                      color: "#78350f", border: "1px solid #fde68a", lineHeight: 1.8,
                    }}>
                      1. Open Google Colab → New Notebook<br/>
                      2. Run: backend/disease_engine/colab_convert_to_onnx.py<br/>
                      3. Download plant_disease_model.onnx<br/>
                      4. Copy to: backend/disease_engine/<br/>
                      5. Restart server
                    </code>
                  </>
                ) : (
                  <>
                    <p style={{ fontSize: "0.82rem", fontWeight: 700, color: "#92400e", marginBottom: 6 }}>
                      Local model not downloaded yet
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "#78350f", marginBottom: 10, lineHeight: 1.5 }}>
                      Run the setup command to download the PlantVillage CNN model.
                      Disease detection runs entirely within this application — no internet required after setup.
                    </p>
                    <code style={{
                      display: "block", fontSize: "0.75rem", fontFamily: "monospace",
                      background: "#fef3c7", padding: "8px 12px", borderRadius: 8,
                      color: "#78350f", border: "1px solid #fde68a",
                    }}>
                      cd backend &amp;&amp; python disease_engine/download_model.py
                    </code>
                    <p style={{ fontSize: "0.72rem", color: "#6b7280", marginTop: 8 }}>
                      After download, restart the server and refresh this page.
                    </p>
                  </>
                )}
              </div>
            </div>
          </div>
        )}


        {/* Upload Zone or Result */}
        {!result && (
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            {/* Drop zone */}
            <div
              onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}
              onClick={() => !scanning && fileInputRef.current?.click()}
              onKeyDown={event => {
                if (!scanning && (event.key === "Enter" || event.key === " ")) {
                  event.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              role="button" tabIndex={0} aria-label="Choose a leaf photo to scan" aria-disabled={scanning}
              style={{
                border: `2px dashed ${dragging ? "var(--g500)" : "var(--border-md)"}`,
                borderRadius: 14, margin: 16,
                background: dragging ? "var(--g50)" : scanning ? "var(--bg-subtle)" : "var(--bg-white)",
                padding: previewURL ? 0 : "36px 24px",
                display: "flex", flexDirection: "column",
                alignItems: "center", justifyContent: "center",
                cursor: scanning ? "default" : "pointer",
                transition: "all 0.2s",
                minHeight: 200, position: "relative", overflow: "hidden",
              }}
            >
              {previewURL ? (
                <>
                  <img
                    src={previewURL} alt="Leaf preview"
                    style={{ width: "100%", maxHeight: 260, objectFit: "cover", borderRadius: 14 }}
                  />
                  {/* Laser scan overlay */}
                  {scanning && (
                    <div style={{
                      position: "absolute", inset: 0, borderRadius: 14,
                      background: "rgba(16,185,129,0.08)",
                      display: "flex", flexDirection: "column",
                      alignItems: "center", justifyContent: "center", gap: 12,
                    }}>
                      <div style={{
                        width: "85%", height: 3, background: "#74885d",
                        boxShadow: "0 0 12px #74885d",
                        animation: "scanLine 2s linear infinite",
                        borderRadius: 2,
                      }} />
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div style={{
                    width: 64, height: 64, borderRadius: "50%",
                    background: "#f4f6f0", display: "flex",
                    alignItems: "center", justifyContent: "center",
                    marginBottom: 14, border: "2px dashed #86efac",
                  }}>
                    {dragging ? <Leaf size={28} color="#74885d" /> : <Upload size={26} color="#74885d" />}
                  </div>
                  <p style={{ fontWeight: 600, color: "var(--text-700)", fontSize: "0.88rem", marginBottom: 4 }}>
                    Drop a leaf image here
                  </p>
                  <p style={{ color: "var(--text-400)", fontSize: "0.75rem" }}>
                    or click to browse — JPG, PNG, WEBP
                  </p>
                </>
              )}
            </div>

            {/* Status */}
            {scanning && (
              <div style={{
                padding: "12px 20px", background: "#f4f6f0",
                borderTop: "1px solid #d1fae5",
                display: "flex", alignItems: "center", gap: 10,
              }}>
                <div style={{
                  width: 14, height: 14, borderRadius: "50%",
                  border: "2px solid #74885d",
                  borderTopColor: "transparent",
                  animation: "spin 0.9s linear infinite",
                }} />
                <span style={{ fontSize: "0.8rem", fontWeight: 600, color: "#4d6042" }}>
                  AI విశ్లేషిస్తోంది... (Analysing locally...)
                </span>
              </div>
            )}

            {/* Camera / Gallery buttons */}
            {!scanning && !previewURL && (
              <div style={{
                display: "flex", gap: 8, padding: "0 16px 16px",
              }}>
                <button type="button" className="btn-secondary" style={{ flex: 1, gap: 8 }}
                  onClick={event => { event.stopPropagation(); fileInputRef.current?.click(); }}>
                  <Upload size={15} /> Gallery
                </button>
                <button type="button" className="btn-secondary" style={{ flex: 1, gap: 8 }}
                  onClick={() => {
                    const i = document.createElement("input");
                    i.type = "file"; i.accept = "image/*"; i.capture = "environment";
                    i.onchange = e => processFile(e.target.files?.[0]);
                    i.click();
                  }}>
                  <Camera size={15} /> Camera
                </button>
              </div>
            )}

            {/* Error */}
            {error && (
              <div style={{
                margin: "0 16px 16px", padding: "12px 14px",
                background: "#fef2f2", border: "1px solid #fecaca",
                borderRadius: 12, display: "flex", gap: 10, alignItems: "flex-start",
              }} role="alert">
                <AlertTriangle size={16} color="#dc2626" style={{ flexShrink: 0, marginTop: 1 }} />
                <div>
                  <p style={{ fontSize: "0.8rem", fontWeight: 700, color: "#991b1b", marginBottom: 3 }}>
                    Analysis Failed
                  </p>
                  <p style={{ fontSize: "0.75rem", color: "#b91c1c" }}>{error}</p>
                  <button type="button" onClick={retryScan} style={{
                    marginTop: 8, fontSize: "0.72rem", fontWeight: 700,
                    color: "#dc2626", background: "none", border: "none",
                    cursor: "pointer", padding: 0, textDecoration: "underline",
                  }}>
                    Retry this image →
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── RESULTS ────────────────────────────────────────────────── */}
        {result && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14, animation: "fadeIn 0.4s ease" }}>

            {/* Main result card */}
            <div className="card">
              {/* Interactive Image Split Inspection Slider */}
              {previewURL && (
                <div className="image-split-view" style={{ marginBottom: 18 }}>
                  <img src={previewURL} alt="Leaf raw capture" className="split-image-layer" />
                  <div className="split-image-overlay" style={{ width: `${splitPos}%` }}>
                    <img
                      src={previewURL}
                      alt="Leaf AI detection filter"
                      className="split-image-layer"
                      style={{
                        filter: result.is_healthy
                          ? "hue-rotate(25deg) contrast(1.2)"
                          : "sepia(0.35) saturate(2) hue-rotate(310deg)",
                      }}
                    />
                    <div
                      style={{
                        position: "absolute",
                        inset: 0,
                        background: result.is_healthy
                          ? "rgba(16, 185, 129, 0.18)"
                          : "rgba(239, 68, 68, 0.22)",
                        mixBlendMode: "overlay",
                      }}
                    />
                  </div>

                  <div className="split-divider-line" style={{ left: `${splitPos}%` }}>
                    <div className="split-divider-handle">↔</div>
                  </div>

                  <input
                    type="range"
                    min="0"
                    max="100"
                    value={splitPos}
                    onChange={e => setSplitPos(Number(e.target.value))}
                    className="parameter-slider-interactive"
                    style={{
                      position: "absolute",
                      inset: 0,
                      width: "100%",
                      height: "100%",
                      opacity: 0,
                      zIndex: 30,
                      cursor: "ew-resize",
                    }}
                    aria-label="Slide to inspect raw leaf photo versus AI diagnosis heatmap"
                  />

                  <div className="split-labels-bar">
                    <span className="split-label-pill">🔬 AI Heatmap Filter</span>
                    <span className="split-label-pill">📷 Raw Photo</span>
                  </div>
                </div>
              )}

              <div style={{
                display: "flex", gap: 14, alignItems: "flex-start",
                paddingBottom: 16, marginBottom: 16,
                borderBottom: "1px dashed #e5e7eb",
              }}>
                {/* Leaf thumbnail */}
                {previewURL && (
                  <img src={previewURL} alt="scanned"
                    style={{
                      width: 90, height: 90, borderRadius: 16,
                      objectFit: "cover", border: "3px solid white",
                      boxShadow: "0 4px 12px rgba(0,0,0,0.12)", flexShrink: 0,
                    }}
                  />
                )}
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
                    {result.is_healthy
                      ? <CheckCircle size={15} color="#74885d" />
                      : <AlertTriangle size={15} color="#f59e0b" />}
                    <span style={{
                      fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      color: result.is_healthy ? "#065f46" : "#92400e",
                    }}>
                      {result.is_healthy ? "Healthy Plant" : "Disease Detected"}
                    </span>
                  </div>
                  <div style={{ fontSize: "1.05rem", fontWeight: 800, color: "#111827", lineHeight: 1.3, marginBottom: 4 }}>
                    {result.english_name}
                  </div>
                  {result.telugu_name && result.telugu_name !== "తెలియని వ్యాధి" && (
                    <div style={{ fontSize: "0.85rem", color: "#6b7280", fontWeight: 500 }}>
                      {result.telugu_name}
                    </div>
                  )}

                  {/* Cache badge */}
                  {result.from_cache && (
                    <span style={{
                      marginTop: 6, display: "inline-flex", alignItems: "center", gap: 4,
                      fontSize: "0.65rem", fontWeight: 600, color: "#6366f1",
                      background: "#eef2ff", padding: "2px 8px", borderRadius: 20,
                    }}>
                      <Database size={9} /> Cached result
                    </span>
                  )}
                </div>
                <ConfidenceGauge value={Math.round(result.confidence)} tier={result.confidence_tier} />
              </div>

              {/* Tier badge */}
              <div style={{
                fontSize: "0.72rem", fontWeight: 600, padding: "6px 12px",
                borderRadius: 20, display: "inline-flex", alignItems: "center", gap: 6,
                background: tierStyle.bg, color: tierStyle.color, marginBottom: 14,
              }}>
                <span style={{ width: 8, height: 8, borderRadius: "50%", background: tierStyle.color }} />
                {tierStyle.label}
              </div>

              {/* Solution cards */}
              {!result.is_healthy && (
                <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                  {[
                    { icon: "💡", label: "Solution", value: result.solution, border: "#74885d" },
                    { icon: "🧪", label: "Fungicide", value: result.fungicide, border: "#3b82f6" },
                    { icon: "🐛", label: "Insecticide", value: result.insecticide, border: "#f59e0b" },
                  ].map(({ icon, label, value, border }) => value && (
                    <div key={label} style={{
                      borderLeft: `5px solid ${border}`, background: "#f8fafc",
                      borderRadius: 12, padding: "12px 14px",
                      display: "flex", gap: 12, alignItems: "flex-start",
                    }}>
                      <span style={{ fontSize: "1.3rem", lineHeight: 1 }}>{icon}</span>
                      <div>
                        <div style={{
                          fontSize: "0.65rem", fontWeight: 700, textTransform: "uppercase",
                          letterSpacing: "0.5px", color: "#9ca3af", marginBottom: 4,
                        }}>
                          {label}
                        </div>
                        <p style={{ fontSize: "0.82rem", color: "#111827", lineHeight: 1.5, margin: 0 }}>
                          {value}
                        </p>
                      </div>
                    </div>
                  ))}
                  {!result.solution && !result.fungicide && !result.insecticide && (
                    <div role="note" style={{ borderLeft: "4px solid #d97706", background: "#fffbeb", borderRadius: 10, padding: "11px 13px", color: "#78350f", fontSize: "0.79rem", lineHeight: 1.5 }}>
                      No crop-specific treatment guidance is available for this scan. Confirm the diagnosis with a qualified local agronomist before treating the plant.
                    </div>
                  )}
                </div>
              )}

              {/* Top-3 alternatives */}
              {result.top_3?.length > 1 && (
                <div style={{ marginTop: 16 }}>
                  <p style={{
                    fontSize: "0.7rem", fontWeight: 700, color: "#9ca3af",
                    textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 8,
                  }}>
                    Could also be
                  </p>
                  {result.top_3.slice(1).map((alt, i) => (
                    <div key={i} style={{
                      display: "flex", justifyContent: "space-between",
                      alignItems: "center", padding: "6px 10px",
                      background: "#f1f5f9", borderRadius: 8, marginBottom: 6,
                    }}>
                      <span style={{ fontSize: "0.78rem", color: "#374151", fontWeight: 500 }}>
                        {alt.english_name}
                      </span>
                      <span style={{
                        fontSize: "0.72rem", fontWeight: 700, color: "#6b7280",
                        background: "#e2e8f0", padding: "2px 8px", borderRadius: 20,
                      }}>
                        {alt.confidence?.toFixed(1)}%
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Feedback card */}
            <div className="card" style={{ padding: "14px 18px" }}>
              {feedbackSent ? (
                <div style={{
                  display: "flex", alignItems: "center", gap: 8,
                  color: "#059669", fontSize: "0.82rem", fontWeight: 600,
                }}>
                  <CheckCircle size={16} /> Feedback recorded. Thank you for helping us review this result.
                </div>
              ) : (
                <>
                  <p style={{
                    fontSize: "0.72rem", fontWeight: 700, color: "#9ca3af",
                    textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 10,
                  }}>
                    Was this accurate?
                  </p>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button type="button" onClick={() => sendFeedback("correct")} disabled={correcting}
                      style={{
                        flex: 1, padding: "10px 0", borderRadius: 12, border: "1.5px solid #a7f3d0",
                        background: "#f4f6f0", color: "#4d6042", fontWeight: 700,
                        fontSize: "0.82rem", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center", gap: 6,
                      }}>
                      <CheckCircle size={14} /> Yes, correct
                    </button>
                    <button type="button" onClick={() => { setFeedbackError(null); setShowCorrect(v => !v); }} disabled={correcting}
                      style={{
                        flex: 1, padding: "10px 0", borderRadius: 12, border: "1.5px solid #fecaca",
                        background: "#fef2f2", color: "#991b1b", fontWeight: 700,
                        fontSize: "0.82rem", cursor: "pointer", display: "flex",
                        alignItems: "center", justifyContent: "center", gap: 6,
                      }}>
                      <XCircle size={14} /> No, wrong
                    </button>
                  </div>
                  {showCorrect && (
                    <div style={{ marginTop: 10 }}>
                      <input
                        id="correctClass" placeholder="Enter correct disease name (English)"
                        aria-label="Correct disease name"
                        style={{
                          width: "100%", padding: "8px 12px", borderRadius: 10,
                          border: "1.5px solid #e5e7eb", fontSize: "0.8rem",
                          marginBottom: 8, boxSizing: "border-box",
                        }}
                      />
                      <button type="button" onClick={submitCorrection} style={{
                        width: "100%", padding: "9px", borderRadius: 10,
                        background: "#1b4332", color: "white", fontWeight: 700,
                        border: "none", fontSize: "0.8rem", cursor: "pointer",
                      }}>
                        Submit Correction
                      </button>
                    </div>
                  )}
                  {feedbackError && <p role="alert" style={{ marginTop: 9, color: "#b91c1c", fontSize: "0.75rem" }}>{feedbackError}</p>}
                </>
              )}
            </div>

            {/* Scope disclaimer */}
            <div style={{
              padding: "10px 14px", borderRadius: 12,
              background: "#fefce8", border: "1px solid #fde68a",
              display: "flex", gap: 8, alignItems: "flex-start",
            }}>
              <Info size={14} color="#92400e" style={{ flexShrink: 0, marginTop: 1 }} />
              <div style={{ fontSize: "0.72rem", color: "#78350f", margin: 0, lineHeight: 1.6 }}>
                <strong>38-class PlantVillage model:</strong><br/>
                Supported crops: {SUPPORTED_CROPS.join(", ")}. Model confidence is not diagnostic accuracy; real field accuracy has not been validated.
              </div>
            </div>

            {/* Scan another */}
            <button type="button" onClick={reset} className="btn-secondary" style={{
              display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
            }}>
              <RotateCcw size={15} /> Scan Another Leaf
            </button>
          </div>
        )}

        {/* Initial scope disclaimer */}
        {!result && !scanning && !previewURL && (
          <div style={{
            borderRadius: 12, overflow: "hidden",
            border: "1.5px solid var(--g200)",
          }}>
            {/* Header */}
            <div style={{
              padding: "10px 14px",
              background: "#eef3e7",
              display: "flex", alignItems: "center", gap: 7,
            }}>
              <Info size={15} color="#708359" style={{ flexShrink: 0 }} />
              <strong style={{ fontSize: "0.77rem", color: "#607446", fontWeight: 550 }}>
                38 leaf classes across 14 crops
              </strong>
            </div>
            {/* Body */}
            <div style={{ background: "var(--g50)", padding: "12px 14px" }}>
              <div>
                <span style={{ fontSize: "0.68rem", fontWeight: 700, color: "#2563eb", display: "inline-flex", alignItems: "center", gap: 4, marginBottom: 5 }}>
                  PlantVillage crops
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {SUPPORTED_CROPS.map(c => (
                    <span key={c} style={{
                      background: "#eff6ff", border: "1px solid #bfdbfe",
                      borderRadius: 99, padding: "2px 9px",
                      fontSize: "0.67rem", fontWeight: 700, color: "#1d4ed8",
                    }}>{c}</span>
                  ))}
                </div>
                <p style={{ fontSize: "0.72rem", color: "#78350f", lineHeight: 1.5, margin: "10px 0 0" }}>
                  Model confidence is not diagnostic accuracy. This PlantVillage model has not been validated on real field images.
                </p>
              </div>
            </div>
          </div>
        )}

        <input
          ref={fileInputRef} type="file" accept="image/*"
          style={{ display: "none" }}
          onChange={e => { const f = e.target.files?.[0]; if (f) processFile(f); }}
        />
      </div>

      {/* ── RIGHT PANEL — History + Analytics ───────────────────────── */}
      <div className="disease-history-column" style={{ display: "flex", flexDirection: "column", gap: 14, minWidth: 0 }}>

        {/* Tab bar */}
        <div style={{
          display: "flex", gap: 0,
          background: "var(--bg-white)",
          border: "1.5px solid var(--border)",
          borderRadius: "var(--r-md)", padding: 4,
          boxShadow: "var(--s-xs)",
        }}>
          {[
            { id: "history",   icon: <Clock size={13} />,    label: "Scan History",
              badge: history.length > 0 ? history.length : null },
            { id: "analytics", icon: <BarChart2 size={13} />, label: "Analytics",
              badge: analytics ? analytics.total_scans : null },
          ].map(tab => (
            <button type="button" key={tab.id} onClick={() => setActiveTab(tab.id)} aria-current={activeTab === tab.id ? "page" : undefined}
              style={{
                flex: 1, padding: "9px 12px",
                borderRadius: 8, border: "none",
                background: activeTab === tab.id
                  ? "linear-gradient(135deg, var(--g100) 0%, var(--g50) 100%)"
                  : "transparent",
                color: activeTab === tab.id ? "var(--g800)" : "var(--text-400)",
                fontWeight: activeTab === tab.id ? 700 : 500,
                fontSize: "0.79rem", cursor: "pointer",
                boxShadow: activeTab === tab.id ? "var(--s-green-sm)" : "none",
                transition: "all 0.18s",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 6,
                fontFamily: "inherit",
              }}>
              {tab.icon} {tab.label}
              {tab.badge != null && (
                <span style={{
                  fontSize: "0.62rem", fontWeight: 800, lineHeight: 1,
                  padding: "2px 7px", borderRadius: 99,
                  background: activeTab === tab.id ? "var(--g500)" : "var(--border)",
                  color: activeTab === tab.id ? "#fff" : "var(--text-400)",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>{tab.badge}</span>
              )}
            </button>
          ))}
        </div>

        {/* ── HISTORY TAB ──────────────────────────────────────────── */}
        {activeTab === "history" && (
          <div className="card" style={{ flex: 1 }}>
            <div className="card-header" style={{ marginBottom: 14 }}>
              <div className="icon-circle"><Clock size={16} /></div>
              <div className="card-title">Recent Scans</div>
              <button type="button" onClick={() => fetchHistory()} disabled={historyLoading} aria-label={historyLoading ? "Refreshing scan history" : "Refresh scan history"} title="Refresh scan history" style={{
                marginLeft: "auto", background: "none", border: "none",
                cursor: "pointer", color: "#9ca3af",
              }}>
                <RefreshCw size={14} className={historyLoading ? "spin" : undefined} />
              </button>
            </div>
            <div className="card-body">
              {historyError && <p role="alert" style={{ color: "#9b3429", fontSize: ".75rem", marginBottom: 10 }}>{historyError}</p>}
              {history.length === 0 ? (
                <div style={{ textAlign: "center", padding: 30, color: "var(--text-400)" }}>
                  <Leaf size={28} style={{ margin: "0 auto 10px", display: "block", opacity: 0.4 }} />
                  <p style={{ fontSize: "0.82rem" }}>{historyLoading ? "Loading scans…" : historyError ? "Scan history is unavailable." : "No scans yet. Upload your first leaf image!"}</p>
                </div>
              ) : (
                history.map(scan => (
                  <HistoryItem key={scan.id} scan={scan} onClick={handleHistoryClick} />
                ))
              )}
            </div>
          </div>
        )}

        {/* ── ANALYTICS TAB ────────────────────────────────────────── */}
        {activeTab === "analytics" && analytics && (
          <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>

            {/* Stats grid */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
              {[
                { label: "Total Scans",        value: analytics.total_scans,     icon: <Microscope size={16} />, color: "#6366f1" },
                { label: "Avg Confidence",     value: `${analytics.avg_confidence}%`, icon: <TrendingUp size={16} />, color: "#74885d" },
                { label: "Uncertain Scans",    value: analytics.uncertain_count, icon: <AlertTriangle size={16} />, color: "#f59e0b" },
                { label: "User Corrections",   value: analytics.correction_count, icon: <Database size={16} />, color: "#8b5cf6" },
              ].map(({ label, value, icon, color }) => (
                <div key={label} className="card" style={{ padding: "14px 16px" }}>
                  <div style={{
                    width: 36, height: 36, borderRadius: 10,
                    background: `${color}18`, color,
                    display: "flex", alignItems: "center", justifyContent: "center",
                    marginBottom: 10,
                  }}>
                    {icon}
                  </div>
                  <div style={{ fontSize: "1.4rem", fontWeight: 800, color: "#111827", lineHeight: 1 }}>
                    {value}
                  </div>
                  <div style={{ fontSize: "0.72rem", color: "#9ca3af", marginTop: 4 }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>

            {/* Most common disease */}
            {analytics.most_common_disease && (
              <div className="card">
                <div className="card-header" style={{ marginBottom: 10 }}>
                  <div className="icon-circle" style={{ background: "#fef3c7", color: "#d97706" }}>
                    <TrendingUp size={16} />
                  </div>
                  <div className="card-title">Most Common Disease</div>
                </div>
                <div className="card-body">
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    alignItems: "center", padding: "10px 14px",
                    background: "#fef9c3", borderRadius: 12,
                    border: "1px solid #fde68a",
                  }}>
                    <span style={{ fontWeight: 700, color: "#78350f", fontSize: "0.85rem" }}>
                      {analytics.most_common_disease.english_name}
                    </span>
                    <span style={{
                      fontWeight: 800, color: "#d97706", fontSize: "1.1rem",
                    }}>
                      ×{analytics.most_common_disease.cnt}
                    </span>
                  </div>
                </div>
              </div>
            )}

            {/* Active learning status */}
            <div className="card">
              <div className="card-header" style={{ marginBottom: 10 }}>
                <div className="icon-circle" style={{ background: "#ede9fe", color: "#7c3aed" }}>
                  <Zap size={16} />
                </div>
                <div className="card-title">Active Learning</div>
              </div>
              <div className="card-body">
                <div style={{ marginBottom: 10 }}>
                  <div style={{
                    display: "flex", justifyContent: "space-between",
                    fontSize: "0.75rem", color: "#6b7280", marginBottom: 6,
                  }}>
                    <span>Corrections collected</span>
                    <span style={{ fontWeight: 700 }}>
                      {analytics.correction_count} / 50
                    </span>
                  </div>
                  <div style={{
                    height: 8, background: "#ede9fe", borderRadius: 4, overflow: "hidden",
                  }}>
                    <div style={{
                      height: "100%", borderRadius: 4,
                      background: analytics.fine_tune_ready ? "#74885d" : "#8b5cf6",
                      width: `${Math.min((analytics.correction_count / 50) * 100, 100)}%`,
                      transition: "width 0.8s ease",
                    }} />
                  </div>
                </div>
                <p style={{ fontSize: "0.75rem", color: "#6b7280", margin: 0 }}>
                  {analytics.fine_tune_ready
                    ? "Corrections are ready for review before a separate retraining run."
                    : `${50 - analytics.correction_count} more corrections before the review queue is ready.`
                  }
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Empty analytics */}
        {activeTab === "analytics" && !analytics && (
          <div className="card" style={{ textAlign: "center", padding: 40 }}>
            <BarChart2 size={32} style={{ margin: "0 auto 10px", opacity: 0.3 }} />
            <p role={analyticsError ? "alert" : "status"} style={{ color: analyticsError ? "#9b3429" : "#6c7b70", fontSize: "0.82rem" }}>
              {analyticsError || (historyLoading ? "Loading analytics…" : "Analytics will appear after your first scan.")}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
