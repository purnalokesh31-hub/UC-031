import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

const KEY = "cropguard.workspace.v1";
const empty = () => ({ version: 1, fields: [], history: [], harvests: [], draft: null, metrics: null });
const Context = createContext(null);
export const newId = () => crypto.randomUUID();
export const toHectares = (area, unit) => Number(area) / (unit === "acre" ? 2.471053814671653 : 1);
export function downloadJSON(value, name) {
  const url = URL.createObjectURL(new Blob([JSON.stringify(value, null, 2)], { type: "application/json" }));
  const link = document.createElement("a"); link.href = url; link.download = name; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
export function WorkspaceProvider({ children }) {
  const [initial] = useState(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return { data: empty(), error: null };
      const value = JSON.parse(raw);
      if (value.version !== 1 || ![value.fields, value.history, value.harvests].every(Array.isArray)) throw Error();
      return { data: { ...empty(), ...value }, error: null };
    } catch { return { data: empty(), error: "Saved workspace could not be read. Existing storage has not been overwritten. Export your current work before leaving." }; }
  });
  const [store, setStore] = useState(initial.data);
  const [storageError, setStorageError] = useState(initial.error);
  const [online, setOnline] = useState(navigator.onLine);
  const [restoreRequest, setRestoreRequest] = useState(null);
  const [savedAt, setSavedAt] = useState(null);
  const [location, setLocation] = useState({ status: "locating", coordinates: null, accuracy: null });
  const locationRequest = useRef(0);
  const currentStore = useRef(initial.data);
  const failedSave = useRef(Boolean(initial.error));
  const requestLocation = useCallback(() => {
    const request = ++locationRequest.current;
    if (!navigator.geolocation || !window.isSecureContext) {
      setLocation({ status: "unavailable", coordinates: null, accuracy: null });
      return;
    }
    setLocation(current => ({ ...current, status: "locating" }));
    try {
      navigator.geolocation.getCurrentPosition(position => {
        if (request !== locationRequest.current) return;
        const { latitude, longitude, accuracy } = position.coords;
        if (!Number.isFinite(latitude) || !Number.isFinite(longitude) ||
            latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
          setLocation({ status: "unavailable", coordinates: null, accuracy: null });
          return;
        }
        setLocation({ status: "ready", coordinates: { latitude, longitude }, accuracy: Number.isFinite(accuracy) ? accuracy : null });
      }, error => {
        if (request !== locationRequest.current) return;
        setLocation({ status: error.code === 1 ? "denied" : "unavailable", coordinates: null, accuracy: null });
      }, { enableHighAccuracy: true, timeout: 15000, maximumAge: 300000 });
    } catch {
      if (request === locationRequest.current) setLocation({ status: "unavailable", coordinates: null, accuracy: null });
    }
  }, []);
  useEffect(() => {
    requestLocation();
    return () => { locationRequest.current += 1; };
  }, [requestLocation]);
  const update = useCallback(change => {
    let current = currentStore.current;
    // Merge against the latest persisted records when another tab has written.
    if (!failedSave.current) {
      try {
        const latest = JSON.parse(localStorage.getItem(KEY) || "null");
        if (latest?.version === 1 && [latest.fields, latest.history, latest.harvests].every(Array.isArray)) current = latest;
      } catch { /* Keep the in-memory workspace if storage becomes unavailable. */ }
    }
    const next = { ...current, ...change(current) };
    currentStore.current = next;
    setStore(next);
    if (initial.error) return; // Preserve unreadable data for recovery.
    try {
      localStorage.setItem(KEY, JSON.stringify(next)); failedSave.current = false;
      setStorageError(null); setSavedAt(new Date());
    } catch {
      failedSave.current = true;
      setStorageError("This device could not save your changes. Export a backup before closing the page; browser storage may be full or disabled.");
    }
  }, [initial]);
  useEffect(() => {
    const synchronize = event => {
      if (event.key !== KEY || !event.newValue || failedSave.current) return;
      try {
        const next = JSON.parse(event.newValue);
        if (next.version !== 1 || ![next.fields, next.history, next.harvests].every(Array.isArray)) return;
        currentStore.current = next; setStore(next);
      } catch { /* Ignore malformed events without discarding local work. */ }
    };
    window.addEventListener("storage", synchronize);
    return () => window.removeEventListener("storage", synchronize);
  }, []);
  useEffect(() => {
    const connected = () => setOnline(navigator.onLine);
    window.addEventListener("online", connected); window.addEventListener("offline", connected);
    return () => { window.removeEventListener("online", connected); window.removeEventListener("offline", connected); };
  }, []);
  const restore = useCallback(draft => {
    update(() => ({ draft })); setRestoreRequest({ id: newId(), draft }); window.location.hash = "dashboard";
  }, [update]);
  return <Context.Provider value={{ store, update, online, restore, restoreRequest, storageError, savedAt, location, requestLocation }}>
    {children}
  </Context.Provider>;
}
export const useWorkspace = () => useContext(Context);

export function WorkspaceStatus() {
  const { online, storageError, savedAt, store, location, requestLocation } = useWorkspace();
  const locationMessage = {
    locating: "Finding your location…",
    ready: "Location ready for new fields",
    denied: "Location blocked · enter coordinates in My fields",
    unavailable: "Location unavailable · enter coordinates in My fields",
  }[location.status];
  return <aside className="workspace-save-status" aria-live="polite">
    <span>{storageError ? "Changes are in memory · export before closing" : !online ? "Offline · drafts remain on this device. Reconnect, then select Analyze yield." : savedAt ? "Saved on this device" : "Workspace stored on this device"}</span>
    <details className="workspace-utilities"><summary>Location & backup</summary><div>
      <span className="workspace-location-status" role="status">{locationMessage}{["denied", "unavailable"].includes(location.status) && <button type="button" onClick={requestLocation}>Try again</button>}</span>
      <button type="button" onClick={() => downloadJSON(store, "cropguard-workspace-backup.json")}>Export backup</button>
    </div></details>
    {storageError && <p role="alert">{storageError}</p>}
  </aside>;
}
