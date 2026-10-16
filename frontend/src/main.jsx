import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.jsx";
import { WorkspaceProvider } from "./lib/WorkspaceStore";
import "./index.css";
import "./dashboard.css";
import "./workspace.css";
import "./features.css";
import "./journey.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <WorkspaceProvider><App /></WorkspaceProvider>
  </React.StrictMode>
);

if ("serviceWorker" in navigator) {
  const registerOfflineShell = () => {
    navigator.serviceWorker.register("/workspace-sw.js").then(() => navigator.serviceWorker.ready).then(registration => {
      const urls = performance.getEntriesByType("resource").map(entry => entry.name).filter(name => {
        const url = new URL(name);
        return url.origin === location.origin && /^\/(src\/|assets\/|node_modules\/\.vite\/|@vite\/|@react-refresh)/.test(url.pathname);
      });
      registration.active?.postMessage({ type: "CACHE_VISITED_ASSETS", urls });
    }).catch(() => {
      // Draft persistence still works if offline page caching is unavailable.
    });
  };
  if (document.readyState === "complete") registerOfflineShell();
  else window.addEventListener("load", registerOfflineShell, { once: true });
}
