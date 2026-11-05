import { Route, Routes } from "react-router-dom";
import AppLayout from "./layouts/AppLayout";
import DashboardPage from "./pages/DashboardPage";
import LedgerPage from "./pages/LedgerPage";
import PerformancePage from "./pages/PerformancePage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="ledger" element={<LedgerPage />} />
        <Route path="performance" element={<PerformancePage />} />
        <Route
          path="*"
          element={<p className="muted">Página não encontrada.</p>}
        />
      </Route>
    </Routes>
  );
}
