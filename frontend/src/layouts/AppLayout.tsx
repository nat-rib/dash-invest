import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

const NAV_GROUPS = [
  {
    label: "Visão geral",
    items: [{ to: "/", label: "Visão geral", icon: "🏠" }],
  },
  {
    label: "Minha carteira",
    items: [
      { to: "/carteira", label: "Posições", icon: "💼" },
      { to: "/ledger", label: "Ledger e operações", icon: "🔄" },
      { to: "/performance", label: "Rentabilidade", icon: "📈" },
    ],
  },
  {
    label: "Investigar",
    items: [
      { to: "/analysis", label: "Análise", icon: "📊" },
      { to: "/fundamentos", label: "Fundamentos", icon: "🏦" },
      { to: "/amortizacao", label: "Amortizar ou investir", icon: "🧮" },
    ],
  },
  {
    label: "Mercado",
    items: [
      { to: "/historico", label: "Histórico patrimonial", icon: "🕒" },
      { to: "/mercado", label: "Cotações", icon: "💹" },
    ],
  },
  {
    label: "Configurações",
    items: [{ to: "/import", label: "Importar carteira", icon: "📥" }],
  },
];

type Theme = "dark" | "light";

function readTheme(): Theme {
  if (typeof document === "undefined") return "dark";
  return document.documentElement.dataset.theme === "light" ? "light" : "dark";
}

function ThemeToggle({
  theme,
  onToggle,
  className = "",
}: {
  theme: Theme;
  onToggle: () => void;
  className?: string;
}) {
  const next = theme === "dark" ? "claro" : "escuro";
  return (
    <button
      type="button"
      className={`theme-toggle ${className}`.trim()}
      onClick={onToggle}
      aria-label={`Ativar tema ${next}`}
      title={`Ativar tema ${next}`}
    >
      <span aria-hidden="true">{theme === "dark" ? "☀️" : "🌙"}</span>
      <span className="theme-label">Tema {next}</span>
    </button>
  );
}

export default function AppLayout() {
  const [menuOpen, setMenuOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(readTheme);
  const location = useLocation();

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "light" ? "#f3f5f9" : "#0a0f1c");
    try {
      localStorage.setItem("dash-invest-theme", theme);
    } catch {
      // Armazenamento indisponível (modo privado); o tema continua válido na sessão.
    }
  }, [theme]);

  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.body.classList.toggle("menu-open", menuOpen);
    return () => document.body.classList.remove("menu-open");
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return;
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpen(false);
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [menuOpen]);

  useEffect(() => {
    function onResize() {
      if (window.innerWidth > 860) setMenuOpen(false);
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const toggleTheme = () => setTheme((current) => (current === "dark" ? "light" : "dark"));

  return (
    <div className={`app-layout ${menuOpen ? "menu-open" : ""}`}>
      <header className="mobile-topbar">
        <button
          type="button"
          className="icon-button"
          onClick={() => setMenuOpen(true)}
          aria-label="Abrir menu de navegação"
          aria-expanded={menuOpen}
          aria-controls="app-sidebar"
        >
          <span aria-hidden="true">☰</span>
        </button>
        <div className="brand">
          <span aria-hidden="true">📊</span> Dash Invest
        </div>
        <ThemeToggle theme={theme} onToggle={toggleTheme} />
      </header>

      <button
        type="button"
        className={`sidebar-overlay ${menuOpen ? "open" : ""}`}
        onClick={() => setMenuOpen(false)}
        aria-label="Fechar menu de navegação"
        aria-hidden={!menuOpen}
        tabIndex={menuOpen ? 0 : -1}
      />

      <aside id="app-sidebar" className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-head">
          <div className="brand">
            <span aria-hidden="true">📊</span> Dash Invest
          </div>
          <button
            type="button"
            className="icon-button"
            onClick={() => setMenuOpen(false)}
            aria-label="Fechar menu de navegação"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>
        <nav aria-label="Navegação principal">
          {NAV_GROUPS.map((group) => (
            <div className="nav-group" key={group.label}>
              <span className="nav-group-label">{group.label}</span>
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
                  onClick={() => setMenuOpen(false)}
                  end
                >
                  <span aria-hidden="true">{item.icon}</span> {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar-footer">
          <ThemeToggle theme={theme} onToggle={toggleTheme} />
          <p className="sidebar-note">
            Interface React + FastAPI. Carteira, ledger e histórico ficam no
            servidor privado e não são enviados a terceiros.
          </p>
        </div>
      </aside>

      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
