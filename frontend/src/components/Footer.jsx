import { Info, Leaf, Microscope, Sprout } from "lucide-react";

export default function Footer({ setPage }) {
  return (
    <footer className="app-footer">
      <div className="app-footer-inner">
        <div className="app-footer-brand">
          <span className="app-footer-mark"><Leaf size={17} /></span>
          <span><strong>CropGuard AI</strong><small>UC-031 · Research prototype</small></span>
        </div>
        <p className="app-footer-note">Yield estimates use synthetic data and have not been validated against real harvests. Disease scanning is a separate pretrained image model.</p>
        <nav className="app-footer-links" aria-label="Footer navigation">
          <button type="button" onClick={() => setPage("dashboard")}><Sprout size={14} /> Yield lab</button>
          <button type="button" onClick={() => setPage("disease")}><Microscope size={14} /> Leaf scan</button>
          <button type="button" onClick={() => setPage("about")}><Info size={14} /> Method</button>
        </nav>
      </div>
    </footer>
  );
}
