import { motion } from "framer-motion";
import { Atom, LayoutDashboard, Info, Leaf, ChevronRight } from "lucide-react";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { id: "about",     label: "About",     icon: Info },
];

export default function Sidebar({ page, setPage }) {
  return (
    <aside className="fixed left-0 top-0 h-full w-64 flex flex-col bg-surface-800 border-r border-white/5 z-50">
      {/* Logo */}
      <div className="p-6 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-brand-500 to-quantum-500 flex items-center justify-center shadow-lg">
              <Leaf size={20} className="text-white" />
            </div>
            <motion.div
              className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-quantum-400"
              animate={{ scale: [1, 1.4, 1], opacity: [1, 0.5, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            />
          </div>
          <div>
            <h1 className="font-bold text-white text-sm leading-tight">CropGuard AI</h1>
            <p className="text-xs text-gray-400">Quantum Yield Intelligence</p>
          </div>
        </div>
      </div>

      {/* Badge */}
      <div className="px-4 py-3">
        <div className="badge-quantum w-full justify-center text-center">
          <Atom size={12} />
          UC-031 · AP Agriculture Dept
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-2 space-y-1">
        {navItems.map(({ id, label, icon: Icon }) => (
          <motion.button
            key={id}
            whileHover={{ x: 4 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => setPage(id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 group
              ${page === id
                ? "bg-brand-600/20 text-brand-400 border border-brand-500/30"
                : "text-gray-400 hover:text-white hover:bg-surface-700"
              }`}
          >
            <Icon size={16} />
            {label}
            {page === id && <ChevronRight size={14} className="ml-auto text-brand-500" />}
          </motion.button>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-white/5">
        <div className="glass-card p-3 text-center">
          <p className="text-xs text-gray-500">Powered by</p>
          <p className="text-xs font-semibold text-quantum-400">Qiskit ZZFeatureMap</p>
          <p className="text-xs text-gray-500 mt-1">4-qubit quantum kernel</p>
        </div>
      </div>
    </aside>
  );
}
