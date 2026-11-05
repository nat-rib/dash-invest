# Dash Invest

Painel pessoal de investimentos com interface React + TypeScript, API FastAPI e domínio financeiro Python. Uma única imagem Docker: Node.js compila o frontend durante o build; o runtime é Python. Carteira, ledger SQLite e histórico permanecem em volume persistente.

## Arquitetura
- Frontend: React 18, TypeScript e Vite, bundle estático responsivo.
- API: FastAPI/Uvicorn em /api, servindo também os arquivos estáticos.
- Domínio: regras e cálculos financeiros Python existentes.
- Persistência: SQLite local; eventos do ledger permanecem append-only.
- Deploy: Docker multi-stage, GHCR, GitHub Actions e Tailscale Serve privado.

A primeira entrega da migração traz Visão geral e consulta da Carteira. As outras áreas permanecem no menu como etapas seguintes. Os módulos Streamlit continuam no repositório durante a transição, mas não são iniciados pelo novo container.

## Desenvolvimento
Backend: python -m pip install -r requirements.txt && uvicorn api.main:app --reload --port 8501
Frontend: cd frontend && npm install && npm run dev
A API local fica em http://localhost:8501; Vite encaminha /api para essa porta. Em produção FastAPI serve frontend/dist na mesma origem.

## Dados
Snapshot: PORTFOLIO_PATH (padrão portfolio.json). Ledger: DASH_INVEST_DB_PATH (data/dash_invest.db). Histórico legado: HISTORY_DB_PATH (data/portfolio_history.db). Snapshot JSON e ledger SQLite continuam fontes distintas. Snapshot não cria transações, fluxos, TWR ou XIRR. Valores sem conversão explícita para BRL não entram no consolidado. Nunca versione dados reais, extratos, bancos, chaves ou secrets.

## Testes e deploy
python -m compileall -q api src && python -m pytest -q
cd frontend && npm install && npm run build
Push em develop executa testes; merge em main publica a imagem e faz deploy privado. A porta local 8501 e o Tailscale Serve permanecem iguais. Consulte deploy/README.md.
