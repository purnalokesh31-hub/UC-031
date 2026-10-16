import BrandMark from "./BrandMark";

export default function Footer({ setPage }) {
  return <footer className="app-footer">
    <div className="app-footer-inner">
      <div className="footer-overview">
        <div className="app-footer-brand"><BrandMark className="brand-mark" /><div><strong>CropGuard<span className="brand-period">.</span></strong><small>Agricultural intelligence</small></div></div>
        <p>Tools for exploring crop yield and leaf imagery with clear model context.</p>
      </div>
      <nav className="app-footer-links" aria-label="Footer navigation">
        <h2>Explore</h2>
        <button type="button" onClick={() => setPage("dashboard")}>Yield analysis</button>
        <button type="button" onClick={() => setPage("fields")}>My fields</button>
        <button type="button" onClick={() => setPage("disease")}>Leaf scan</button>
      </nav>
      <div className="footer-methods">
        <h2>About this research</h2>
        <p>Estimates are exploratory and have not been validated on real harvests.</p>
        <button type="button" onClick={() => setPage("about")}>Methods and limitations →</button>
      </div>
      <div className="footer-bottom"><span>© {new Date().getFullYear()} CropGuard</span><span>Research workspace</span></div>
    </div>
  </footer>;
}
