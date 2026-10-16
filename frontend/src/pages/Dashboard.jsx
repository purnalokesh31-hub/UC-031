import { useCallback, useEffect, useRef, useState, lazy, Suspense } from "react";
import { ArrowRight, BarChart3, BookOpen, Info, Leaf, RefreshCw, SlidersHorizontal, Sprout } from "lucide-react";
import { api, isCancel } from "../api";
import InputForm from "../components/InputForm";
import { useWorkspace, newId } from "../lib/WorkspaceStore";
import QuantumWalkthrough from "../components/QuantumWalkthrough";
import MetricsBadge from "../components/MetricsBadge";

const YieldComparison = lazy(() => import("../components/YieldComparison"));
const RecommendationsPanel = lazy(() => import("../components/RecommendationsPanel"));

export default function Dashboard({ active }) {
  const { store, update } = useWorkspace();
  const [result, setResult] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [allMetrics, setAllMetrics] = useState(store.metrics);
  const [selectedCrop, setSelectedCrop] = useState(store.draft?.crop || "Rice");
  const [apiStatus, setApiStatus] = useState("checking");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [contextOpen, setContextOpen] = useState(false);
  const [editRequest, setEditRequest] = useState(0);
  const [isStale, setIsStale] = useState(false);
  const predictionController = useRef(null);
  const metricsController = useRef(null);
  const metrics = (!isStale && result?.metrics) || allMetrics?.[selectedCrop] || null;

  useEffect(() => {
    if (!result || !active) return;
    const output = document.getElementById("yield-result");
    output?.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 900px)").matches) {
      output?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
    }
  }, [result, active]);

  const fetchMetrics = useCallback(async () => {
    metricsController.current?.abort();
    const controller = new AbortController();
    metricsController.current = controller;
    const signal = controller.signal;
    setRefreshing(true);
    try {
      const [, response] = await Promise.all([
        api.get("/health", { timeout: 3000, signal }),
        api.get("/metrics", { timeout: 5000, signal }),
      ]);
      setApiStatus("online");
      if (response.data.error) throw new Error(response.data.error);
      setAllMetrics(response.data);
      update(() => ({ metrics: response.data }));
    } catch (requestError) {
      if (!isCancel(requestError)) setApiStatus("offline");
    } finally {
      if (metricsController.current === controller) setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchMetrics();
    return () => {
      metricsController.current?.abort();
      predictionController.current?.abort();
    };
  }, [fetchMetrics]);

  const handlePredict = useCallback(async (formValues, scenarioContext = {}) => {
    predictionController.current?.abort();
    const controller = new AbortController();
    predictionController.current = controller;
    setIsLoading(true);
    setError(null);
    setSelectedCrop(formValues.crop_type);
    setIsStale(true);
    try {
      const response = await api.post("/predict/both", formValues, {
        timeout: 30000,
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setApiStatus("online");
        const saved = { ...response.data, id: newId(), inputs: formValues, context: scenarioContext, created_at: new Date().toISOString() };
        setResult(saved);
        setIsStale(false);
        update(current => ({ history: [saved, ...current.history] }));
        setRecommendations(response.data.recommendations);
      }
    } catch (requestError) {
      if (!isCancel(requestError)) {
        if (!requestError.response) setApiStatus("offline");
        const detail = requestError.response?.data?.detail;
        setError(Array.isArray(detail) ? detail.map(item => item.msg).join("; ")
          : typeof detail === "string" ? detail
          : "The prediction service could not be reached. Please try again in a moment.");
      }
    } finally {
      if (predictionController.current === controller) setIsLoading(false);
    }
  }, []);

  const handleCropChange = crop => {
    setError(null);
    setSelectedCrop(crop);
    setIsStale(true);
  };

  const handleInputsChange = () => {
    setError(null);
    predictionController.current?.abort();
    setIsStale(true);
    setIsLoading(false);
  };

  return (
    <main className="page-content dashboard-page direct-workspace">
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <h1>Yield estimate</h1>
          <p>Choose a crop, enter your conditions, and compare the estimates.</p>
        </div>
        <div className="dashboard-hero-aside">
          <div className={`api-status api-status-${apiStatus}`} role="status">
            <span className="api-status-dot" />
            {apiStatus === "online" ? "Ready to estimate" : apiStatus === "offline" ? "Service unavailable" : "Connecting…"}
          </div>
          {apiStatus === "offline" && <button type="button" className="refresh-button" disabled={refreshing} onClick={() => fetchMetrics()}>
            <RefreshCw size={14} className={refreshing ? "spin" : ""} /> {refreshing ? "Reconnecting…" : "Reconnect"}
          </button>}
        </div>
      </section>

      <div className="workspace-notice"><BookOpen size={17} /><p><strong>Research demo</strong> Estimates use synthetic training data and are not validated on real harvests.</p><a href="#about">About the data <ArrowRight size={14} /></a></div>

      <div className="dashboard-grid">
        <section className="dashboard-input-column" aria-label="Field conditions">
          <InputForm
            onSubmit={handlePredict}
            isLoading={isLoading}
            allMetrics={allMetrics}
            onCropChange={handleCropChange}
            onValuesChange={handleInputsChange}
            editRequest={editRequest}
            submitError={error}
          />
        </section>

        <section id="yield-result" tabIndex={-1} className="dashboard-output-column" aria-label="Yield estimate and context">
          {result && isStale && !isLoading && <p className="previous-result-note" role="status"><Info size={18} /><span><strong>Previous estimate</strong> These results use your previously submitted conditions. Estimate again to apply your current values.</span></p>}
          {result || isLoading ? (
            <Suspense fallback={<div className="output-placeholder" role="status">Loading model comparison…</div>}>
              <YieldComparison result={result} isLoading={isLoading}
                onEdit={() => setEditRequest(value => value + 1)} />
            </Suspense>
          ) : (
            <div className="output-placeholder output-empty">
              <div className="result-empty-icon"><BarChart3 size={25} strokeWidth={1.7} /></div>
              <h2>Your estimate, at a glance</h2>
              <p>Select <strong>Estimate yield</strong> to see your results. Trying it for the first time? Start with the sample values.</p>
              <div className="estimate-preview-list">
                <div><Sprout size={18} /><span>Yield & field total</span><small>Tonnes or quintals</small></div>
                <div><SlidersHorizontal size={18} /><span>Prediction range</span><small>90% interval</small></div>
                <div><BarChart3 size={18} /><span>Side-by-side comparison</span><small>Both models</small></div>
              </div>
            </div>
          )}
          {result && <><p className="feature-help">Analysis saved on this device. <a href="#history">Open history, compare scenarios or record harvest</a></p><QuantumWalkthrough result={result} /></>}
          {recommendations && !isStale && <details className="context-details" open={contextOpen} onToggle={event => setContextOpen(event.currentTarget.open)}><summary>Demo baseline & yield context</summary>{contextOpen && <Suspense fallback={<p role="status">Loading yield context…</p>}><RecommendationsPanel data={recommendations} isLoading={false} /></Suspense>}</details>}
        </section>
      </div>

      <MetricsBadge metrics={metrics} apiStatus={apiStatus} />
      <p className="dashboard-disclaimer"><Leaf size={14} /> Explore scenarios here; use local expertise and measured field data for agricultural decisions.</p>
    </main>
  );
}
