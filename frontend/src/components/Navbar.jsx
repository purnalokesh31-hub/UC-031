import { Leaf, Microscope, Sprout, Info } from "lucide-react";

export default function Navbar({ page, setPage }) {
  return (
    <nav className="topnav" aria-label="Main navigation">
      {/* Logo */}
      <button type="button" className="nav-logo-wrap" onClick={() => setPage("dashboard")} aria-label="CropGuard AI home">
        <div className="nav-logo-icon">
          <Leaf size={16} color="#fff" />
        </div>
        <div>
          <span className="nav-logo-text">CropGuard AI</span>
          <span className="nav-logo-sub">Your crop workspace</span>
        </div>
      </button>

      {/* Links */}
      <div className="nav-links">
        {[
          { id: "dashboard", label: "Yield lab", icon: Sprout },
          { id: "disease",   label: "Leaf scan", icon: Microscope },
          { id: "about",     label: "Method", icon: Info },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            id={`nav-${id}`}
            type="button"
            aria-current={page === id ? "page" : undefined}
            className={`nav-link${page === id ? " active" : ""}`}
            onClick={() => setPage(id)}
          >
            <Icon size={15} strokeWidth={1.8} />
            {label}
          </button>
        ))}
      </div>

      {/* Tag */}
      <div className="nav-tag"><span /> Research preview</div>
    </nav>
  );
}
