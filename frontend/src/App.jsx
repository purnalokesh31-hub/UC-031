import { useEffect, useState, lazy, Suspense } from "react";
const Dashboard = lazy(() => import("./pages/Dashboard"));
const About = lazy(() => import("./pages/About"));
const DiseaseScan = lazy(() => import("./pages/DiseaseScan"));
import Navbar from "./components/Navbar";
import Footer from "./components/Footer";

const PAGES = ["dashboard", "disease", "about"];
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
      <div id="app-content" tabIndex={-1} className="app-content">
        <Suspense fallback={<p className="page-content" role="status">Loading…</p>}>
          {visited.has("dashboard") && <div hidden={page !== "dashboard"}><Dashboard active={page === "dashboard"} /></div>}
          {visited.has("disease") && <div hidden={page !== "disease"} className="page-content scan-page"><DiseaseScan /></div>}
          {visited.has("about") && <div hidden={page !== "about"}><About /></div>}
        </Suspense>
      </div>
      <Footer setPage={setPage} />
    </div>
  );
}
