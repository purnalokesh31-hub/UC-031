import BrandMark from "./BrandMark";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ChevronDown, Sprout, BookOpen, Clock, Microscope, Camera, Info, Menu, X } from "lucide-react";

const NAV_ITEMS = [
  { id: "dashboard", label: "Yield analysis", icon: Sprout },
  { id: "fields", label: "My fields", icon: BookOpen },
  { id: "history", label: "History", icon: Clock },
  { id: "research", label: "Research", icon: Microscope },
  { id: "disease", label: "Leaf scan", icon: Camera },
  { id: "about", label: "Method & data", icon: Info },
];

export default function Navbar({ page, setPage }) {
  const moreMenu = useRef(null);
  const navContainerRef = useRef(null);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pillStyle, setPillStyle] = useState({ left: 0, width: 0, opacity: 0 });
  const secondaryPages = [{ id: "research", label: "Research" }, { id: "disease", label: "Leaf scan" }, { id: "about", label: "Method & data" }];

  useLayoutEffect(() => {
    const updatePill = () => {
      const activeBtn = navContainerRef.current?.querySelector(`#nav-${page}`);
      if (activeBtn) {
        setPillStyle({
          left: activeBtn.offsetLeft,
          width: activeBtn.offsetWidth,
          opacity: 1,
        });
      }
    };
    updatePill();
    window.addEventListener("resize", updatePill);
    return () => window.removeEventListener("resize", updatePill);
  }, [page]);

  useEffect(() => {
    if (moreMenu.current) moreMenu.current.open = false;
    setMobileOpen(false);
  }, [page]);

  useEffect(() => {
    const close = event => {
      if (moreMenu.current && !moreMenu.current.contains(event.target)) moreMenu.current.open = false;
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);

  return (
    <>
      <nav className="topnav" aria-label="Main navigation">
        <button type="button" className="nav-logo-wrap" onClick={() => setPage("dashboard")} aria-label="CropGuard home">
          <BrandMark className="brand-mark" />
          <div>
            <span className="nav-logo-text">CropGuard<span className="brand-period">.</span></span>
            <span className="nav-logo-sub">Agricultural intelligence · AI Platform</span>
          </div>
        </button>

        <div className="nav-links" ref={navContainerRef}>
          {/* Animated sliding indicator pill */}
          <div
            className="nav-slider-pill"
            style={{
              transform: `translateX(${pillStyle.left}px)`,
              width: `${pillStyle.width}px`,
              opacity: pillStyle.opacity,
            }}
            aria-hidden="true"
          />

          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              id={`nav-${id}`}
              type="button"
              aria-current={page === id ? "page" : undefined}
              className={`nav-link${secondaryPages.some(item => item.id === id) ? " nav-secondary" : ""}${page === id ? " active" : ""}`}
              onClick={() => setPage(id)}
            >
              <Icon size={15} className="nav-icon" />
              <span>{label}</span>
            </button>
          ))}

          <details
            ref={moreMenu}
            className={`nav-more${secondaryPages.some(item => item.id === page) ? " active" : ""}`}
            onKeyDown={event => {
              if (event.key === "Escape") {
                moreMenu.current.open = false;
                moreMenu.current.querySelector("summary")?.focus();
              }
            }}
          >
            <summary>More <ChevronDown size={14} /></summary>
            <div className="nav-more-links">
              {secondaryPages.map(({ id, label }) => (
                <button
                  key={id}
                  type="button"
                  aria-current={page === id ? "page" : undefined}
                  onClick={() => {
                    moreMenu.current.open = false;
                    setPage(id);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
          </details>
        </div>

        <div className="nav-tag" title="Connected to Agricultural Research Intelligence">
          <span /> Research workspace
        </div>

        {/* Mobile menu toggle */}
        <button
          type="button"
          className="mobile-nav-toggle"
          onClick={() => setMobileOpen(open => !open)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X size={20} /> : <Menu size={20} />}
        </button>
      </nav>

      {/* Mobile Sliding Drawer */}
      {mobileOpen && (
        <div className="slide-drawer-backdrop" onClick={() => setMobileOpen(false)}>
          <div className="slide-drawer-panel mobile-nav-drawer" onClick={e => e.stopPropagation()}>
            <div className="slide-drawer-header">
              <h3>
                <BrandMark style={{ width: 28, height: 28 }} />
                <span>CropGuard Navigation</span>
              </h3>
              <button type="button" className="slide-drawer-close" onClick={() => setMobileOpen(false)} aria-label="Close menu">
                <X size={18} />
              </button>
            </div>
            <div className="slide-drawer-body">
              <div className="mobile-drawer-links">
                {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    type="button"
                    className={`mobile-drawer-btn${page === id ? " active" : ""}`}
                    onClick={() => {
                      setPage(id);
                      setMobileOpen(false);
                    }}
                  >
                    <Icon size={18} />
                    <span>{label}</span>
                  </button>
                ))}
              </div>
              <div className="mobile-drawer-footer">
                <div className="nav-tag">
                  <span /> Quantum & Classical Agritech
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
