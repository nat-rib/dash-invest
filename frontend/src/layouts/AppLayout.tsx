import { NavLink, Outlet } from "react-router-dom";

const NAV = [
  { to: "/", label: "Visão geral", icon: "🏠" },
  { to: "/ledger", label: "Ledger e operações", icon: "🔄" },
  { to: "/performance", label: "Rentabilidade", icon: "📈" },
  { to: "/import", label: "Importar carteira", icon: "📥" },
];

export default function AppLayout() {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="brand">
          <span aria-hidden="true">📊</span> Dash Invest
        </div>
        <nav>
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
              end
            >
              <span aria-hidden="true">{item.icon}</span> {item.label}
            </NavLink>
          ))}
        </nav>
        <p className="sidebar-note">
          Migração Streamlit → React em andamento: demais telas continuam no
          aplicativo Streamlit até a paridade funcional ser confirmada.
        </p>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
