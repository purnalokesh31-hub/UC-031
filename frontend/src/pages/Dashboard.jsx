import { useCallback, useEffect, useRef, useState, lazy, Suspense } from "react";
import { Activity, ArrowDown, Leaf, RefreshCw } from "lucide-react";
import { api, isCancel } from "../api";
import InputForm from "../components/InputForm";
import RecommendationsPanel from "../components/RecommendationsPanel";
import MetricsBadge from "../components/MetricsBadge";

const YieldComparison = lazy(() => import("../components/YieldComparison"));

export default function Dashboard({ active }) {
  const [result, setResult] = useState(null);
  const [recommendations, setRecommendations] = useState(null);
  const [allMetrics, setAllMetrics] = useState(null);
  const [selectedCrop, setSelectedCrop] = useState("Rice");
  const [apiStatus, setApiStatus] = useState("checking");
  const [isLoading, setIsLoading] = useState(false);
  const [comparison, setComparison] = useState(null);
  const [comparisonLoading, setComparisonLoading] = useState(false);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const predictionController = useRef(null);
  const comparisonController = useRef(null);
  const lastFormValues = useRef(null);
  const metricsController = useRef(null);
  const metrics = result?.metrics || allMetrics?.[selectedCrop] || null;

  useEffect(() => {
    if (!result || !active) return;
    const output = document.getElementById("yield-result");
    output?.focus({ preventScroll: true });
    if (window.matchMedia("(max-width: 1000px)").matches) {
      output?.scrollIntoView({ behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth", block: "start" });
    }
  }, [result]);

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
      comparisonController.current?.abort();
    };
  }, [fetchMetrics]);

  const handlePredict = useCallback(async formValues => {
    predictionController.current?.abort();
    comparisonController.current?.abort();
    lastFormValues.current = formValues;
    setComparison(null);
    setComparisonLoading(false);
    const controller = new AbortController();
    predictionController.current = controller;
    setIsLoading(true);
    setError(null);
    setSelectedCrop(formValues.crop_type);
    setResult(null);
    setRecommendations(null);
    try {
      const response = await api.post("/predict/selected", formValues, {
        timeout: 30000,
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        setApiStatus("online");
        setResult({ ...response.data, inputs: formValues, created_at: new Date().toISOString() });
        setRecommendations(response.data.recommendations);
      }
    } catch (requestError) {
      if (!isCancel(requestError)) {
        const detail = requestError.response?.data?.detail;
        setError(Array.isArray(detail) ? detail.map(item => item.msg).join("; ")
          : typeof detail === "string" ? detail
          : "The prediction service could not be reached. Check the local API and try again.");
      }
    } finally {
      if (predictionController.current === controller) setIsLoading(false);
    }
  }, []);

  const handleCompare = useCallback(async family => {
    if (!lastFormValues.current) return;
    comparisonController.current?.abort();
    const controller = new AbortController();
    comparisonController.current = controller;
    setComparison(null);
    setComparisonLoading(true);
    setError(null);
    try {
      const response = await api.post(`/predict/${family}`, lastFormValues.current, {
        timeout: 30000,
        signal: controller.signal,
      });
      if (!controller.signal.aborted) {
        if (response.data.release_id !== result?.release_id) {
          setError("The models were updated. Estimate yield again to compare models from the same release.");
        } else setComparison({ family, data: response.data });
      }
    } catch (requestError) {
      if (!isCancel(requestError)) {
        setError("The additional model comparison failed. Your selected estimate is still available.");
      }
    } finally {
      if (comparisonController.current === controller) setComparisonLoading(false);
    }
  }, [result]);

  const handleCropChange = crop => {
    setError(null);
    comparisonController.current?.abort();
    lastFormValues.current = null;
    setComparison(null);
    setComparisonLoading(false);
    setSelectedCrop(crop);
    setResult(null);
    setRecommendations(null);
  };

  const handleInputsChange = () => {
    setError(null);
    predictionController.current?.abort();
    comparisonController.current?.abort();
    lastFormValues.current = null;
    setResult(null);
    setRecommendations(null);
    setComparison(null);
    setIsLoading(false);
    setComparisonLoading(false);
  };

  return (
    <main className="page-content dashboard-page">
      <section className="dashboard-hero">
        <div className="dashboard-hero-copy">
          <div className="dashboard-eyebrow"><span /> THE YIELD WORKSPACE</div>
          <h1>A clearer view of your <span>field.</span></h1>
          <p>Choose your crop. Add field conditions. Explore the estimated harvest.</p>
        </div>
        <div className="dashboard-hero-aside">
          <div className={`api-status api-status-${apiStatus}`} role="status">
            <span className="api-status-dot" />
            {apiStatus === "online" ? "Models ready" : apiStatus === "offline" ? "Service unavailable" : "Connecting…"}
          </div>
          <button type="button" className="refresh-button" disabled={refreshing} onClick={() => fetchMetrics()}>
            <RefreshCw size={15} className={refreshing ? "spin" : ""} /> {refreshing ? "Refreshing…" : "Refresh models"}
          </button>
        </div>
      </section>

      <div className="workspace-notice"><Leaf size={17} /><p><strong>A space to explore.</strong> This demo learns from synthetic data. Estimates are for research and have not been validated on real harvests.</p></div>

      {error && <div className="dashboard-error" role="alert"><Activity size={17} /> {error}</div>}

      <div className="dashboard-grid">
        <section className="dashboard-input-column" aria-label="Field conditions">
          <InputForm
            onSubmit={handlePredict}
            isLoading={isLoading}
            allMetrics={allMetrics}
            onCropChange={handleCropChange}
            onValuesChange={handleInputsChange}
          />
        </section>

        <section id="yield-result" tabIndex={-1} className="dashboard-output-column" aria-label="Yield estimate and context">
          {result || isLoading ? (
            <Suspense fallback={<div className="output-placeholder" role="status">Loading model comparison…</div>}>
              <YieldComparison result={result} isLoading={isLoading} comparison={comparison}
                comparisonLoading={comparisonLoading} onCompare={handleCompare}
                onEdit={() => { document.getElementById("crop-select")?.focus({ preventScroll: true }); document.getElementById("field-form")?.scrollIntoView({ behavior: "smooth", block: "start" }); }} />
            </Suspense>
          ) : (
            <div className="output-placeholder output-empty">
              <p className="placeholder-eyebrow">02 / YOUR ESTIMATE</p>
              <div className="field-illustration" aria-hidden="true"><Leaf size={44} strokeWidth={1.3} /><i /><i /><i /></div>
              <h2>Every harvest starts here.</h2>
              <p>Set up your field on the left, or use the example values to try it. Your estimated yield and uncertainty range will appear here.</p>
              <div className="empty-steps"><span>1. Choose a crop</span><span>2. Check conditions</span><span>3. Estimate yield</span></div>
              <a className="mobile-form-link" href="#field-form" onClick={event => { event.preventDefault(); document.getElementById("crop-select")?.focus(); }}><ArrowDown size={16} /> Set up your field</a>
            </div>
          )}
          {recommendations && <details className="context-details"><summary>Demo baseline & yield context</summary><RecommendationsPanel data={recommendations} isLoading={false} /></details>}
        </section>
      </div>

      <MetricsBadge metrics={metrics} apiStatus={apiStatus} />
      <p className="dashboard-disclaimer">For research and demonstration only. This model has not been validated against measured harvests. Do not use this estimate alone to make financial, planting, fertilizer, or treatment decisions.</p>
    </main>
  );
}
