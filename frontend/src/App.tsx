import { Route, Routes } from "react-router-dom";
import AnalysisPage from "./pages/AnalysisPage";
import AmortizacaoPage from "./pages/AmortizacaoPage";
import AppLayout from "./layouts/AppLayout";
import CarteiraPage from "./pages/CarteiraPage";
import DashboardPage from "./pages/DashboardPage";
import FitPage from "./pages/FitPage";
import FundamentalsPage from "./pages/FundamentalsPage";
import HistoricoPage from "./pages/HistoricoPage";
import ImportPage from "./pages/ImportPage";
import LedgerPage from "./pages/LedgerPage";
import MercadoPage from "./pages/MercadoPage";
import PerformancePage from "./pages/PerformancePage";
import RiskPage from "./pages/RiskPage";
import ScreenerPage from "./pages/ScreenerPage";

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="carteira" element={<CarteiraPage />} />
        <Route path="ledger" element={<LedgerPage />} />
        <Route path="performance" element={<PerformancePage />} />
        <Route path="import" element={<ImportPage />} />
        <Route path="analysis" element={<AnalysisPage />} />
        <Route path="fundamentos" element={<FundamentalsPage />} />
        <Route path="risco" element={<RiskPage />} />
        <Route path="screener" element={<ScreenerPage />} />
        <Route path="fit" element={<FitPage />} />
        <Route path="historico" element={<HistoricoPage />} />
        <Route path="mercado" element={<MercadoPage />} />
        <Route path="amortizacao" element={<AmortizacaoPage />} />
        <Route
          path="*"
          element={<p className="muted">Página não encontrada.</p>}
        />
      </Route>
    </Routes>
  );
}
