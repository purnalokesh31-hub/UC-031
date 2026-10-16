import { useEffect, useState, lazy, Suspense } from "react";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const About = lazy(() => import("./pages/About"));
const DiseaseScan = lazy(() => import("./pages/DiseaseScan"));
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";
import { WorkspaceStatus } from "./lib/WorkspaceStore";
const FieldNotebook = lazy(() => import("./pages/FieldNotebook"));
const AnalysisHistory = lazy(() => import("./pages/AnalysisHistory"));
const ResearchDashboard = lazy(() => import("./pages/ResearchDashboard"));

const PAGES = ["dashboard", "disease", "about", "fields", "history", "research"];
const readPage = () => PAGES.includes(window.location.hash.slice(1)) ? window.location.hash.slice(1) : "dashboard";

export default function App() {
  const [page, updatePage] = useState(readPage);
  const [visited, setVisited] = useState(() => new Set([readPage()]));
  useEffect(() => {
    const onNavigation = () => {
      const next = readPage();
      setVisited(current => new Set([...current, next]));
      updatePage(next);
      window.scrollTo({ top: 0, behavior: "instant" });
      document.getElementById("app-content")?.focus({ preventScroll: true });
    };
    window.addEventListener("hashchange", onNavigation);
    return () => window.removeEventListener("hashchange", onNavigation);
  }, []);
  const setPage = next => { window.location.hash = next; };
  return (
    <div className="app-shell">
      <button className="skip-link" onClick={() => document.getElementById("app-content")?.focus()}>Skip to content</button>
      <Navbar page={page} setPage={setPage} />
      <WorkspaceStatus />
      <div id="app-content" tabIndex={-1} className="app-content">
        <Suspense fallback={<p className="page-content" role="status">Loading…</p>}>
          {visited.has("dashboard") && <div hidden={page !== "dashboard"} className={`page-slide-panel ${page === "dashboard" ? "active-page" : ""}`}><Dashboard active={page === "dashboard"} /></div>}
          {visited.has("disease") && <div hidden={page !== "disease"} className={`page-content scan-page page-slide-panel ${page === "disease" ? "active-page" : ""}`}><DiseaseScan /></div>}
          {visited.has("fields") && <div hidden={page !== "fields"} className={`page-slide-panel ${page === "fields" ? "active-page" : ""}`}><FieldNotebook /></div>}
          {visited.has("history") && <div hidden={page !== "history"} className={`page-slide-panel ${page === "history" ? "active-page" : ""}`}><AnalysisHistory /></div>}
          {visited.has("research") && <div hidden={page !== "research"} className={`page-slide-panel ${page === "research" ? "active-page" : ""}`}><ResearchDashboard /></div>}
          {visited.has("about") && <div hidden={page !== "about"} className={`page-slide-panel ${page === "about" ? "active-page" : ""}`}><About /></div>}
        </Suspense>
      </div>
      <Footer setPage={setPage} />
    </div>
  );
}
