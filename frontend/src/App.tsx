import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import LedgerPage from "./pages/LedgerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="ledger" element={<LedgerPage />} />
        <Route
          path="*"
          element={<p className="muted">Página não encontrada.</p>}
        />
      </Route>
    </Routes>
  );
}
