# Dashboard pessoal de investimentos

Dashboard privado em Python + React para acompanhar uma carteira, operações e dados de mercado. A aplicação mantém o snapshot JSON legado e o ledger SQLite como fontes distintas até que exista uma reconciliação explícita entre eles.

## Instalação e uso

Requer Python 3.11 ou superior e Node.js 22 para compilar o frontend.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

cd frontend && npm install && npm run build && cd ..

cp .env.example .env          # preencha as variáveis necessárias
set -a; source .env; set +a
python -m uvicorn api.main:app --host 127.0.0.1 --port 8501
```

Abra a URL exibida no terminal. Use **Importar carteira** para validar e substituir o snapshot JSON por inteiro. Alternativamente, copie um JSON válido para `portfolio.json` na raiz do projeto.

Use `portfolio.example.json` como referência: todo o conteúdo é fictício. Nunca versione seu `portfolio.json` real.

## Stack React + FastAPI

As telas foram migradas para React + TypeScript conforme o
[roadmap](docs/ROADMAP_REACT_MIGRATION.md); as regras financeiras continuam nos
módulos `src/` e são expostas pela API em `api/`. As fases 0 a 6 estão
concluídas: todas as telas operam na interface React e o container único serve
o frontend compilado pelo FastAPI.

Desenvolvimento local do frontend:

```bash
uvicorn api.main:app --port 8501   # API + static do build
cd frontend && npm install && npm run dev   # Vite em http://localhost:5173 (proxy /api → 8501)
cd frontend && npm run build       # gera frontend/dist servido pelo FastAPI
```

Run local com a interface React servida pelo FastAPI:

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8501
```

A interface cobre todas as funcionalidades: Visão geral, Posições, Ledger, Rentabilidade, Análise e Detalhes, Importar carteira, Histórico patrimonial, Cotações e Amortizar ou investir.

## Interface e fontes de dados

A Visão geral apresenta patrimônio e alocação conhecidos a partir do snapshot JSON configurado em `PORTFOLIO_PATH`. Ela informa essa origem explicitamente e não combina automaticamente o snapshot com o ledger SQLite. Rentabilidade TWR/XIRR permanece na seção **Minha carteira → Rentabilidade**, pois depende de fluxos e avaliações suficientes. Benchmark ainda não é calculado.

A interface React em `frontend/` usa navegação agrupada, dashboard consolidado pelo endpoint `GET /api/overview` e tabelas que viram cartões no celular. A validação automatizada de overflow cobre 360 px, 390 px, 430 px e desktop.\n\n## Dados e cálculos

- Classes aceitas: `acao`, `fii`, `renda_fixa`, `etf`, `exterior`, `cripto`, `fundo`, `outros`, `caixa` e `credito_privado_coletivo`.
- O valor vem de `current_value`, quando informado; caso contrário, de `quantity × current_price`.
- Patrimônio consolidado soma valores conhecidos em BRL e valores estrangeiros somente quando houver taxa e valor de conversão para BRL registrados explicitamente. Não ocorre conversão implícita.
- Ganho e rentabilidade só aparecem quando custo e valor atual são calculáveis e comparáveis.
- Um snapshot não fornece histórico: não são calculados TWR, XIRR, proventos ou retorno acumulado.

## Privacidade

Os dados ficam somente nos arquivos locais usados pela aplicação e não são enviados a serviços externos por este projeto. Isso não significa que estejam criptografados: a proteção em repouso depende do FileVault do macOS ou de um volume criptografado configurado por você. Não coloque senhas, tokens ou credenciais no JSON.

## Dados de mercado opcionais

A página **Mercado** pode consultar cotações e histórico diário no Alpha Vantage. A chave é lida de `ALPHA_VANTAGE_API_KEY` no ambiente do processo:

```bash
cp .env.example .env          # preencha ALPHA_VANTAGE_API_KEY
set -a; source .env; set +a   # carrega no shell antes de subir a API
```

Em produção o `deploy/compose.yaml` injeta a variável a partir do `.env` da VPS. Nunca versione `.env` ou `secrets.toml`, e nunca passe a chave como `ARG`/`ENV` do `Dockerfile` — ela ficaria na imagem. A consulta envia somente o símbolo do ativo ao Alpha Vantage — não envia saldos, quantidades ou instituições. Por padrão, ações, FIIs e ETFs em BRL usam o sufixo `.SAO`; se necessário, defina `market_symbol` na posição do JSON. A atualização de preços sempre mostra uma prévia e requer confirmação antes de substituir o snapshot.

## Fundamentos de companhias (CVM)

A ingestão de demonstrações financeiras usa os dados abertos da CVM (DFP) e grava observações com proveniência no SQLite:

```bash
python -m jobs.ingest_cvm --year 2024
# dentro do container em produção:
docker exec dash-invest python -m jobs.ingest_cvm --year 2024
```

Cada linha guarda provedor, CNPJ do emissor, métrica, período, data de publicação, link do documento e o payload bruto. Reingestões são idempotentes e reapresentações marcam a versão anterior como substituída, sem apagar histórico. Consulta pelos endpoints `GET /api/data/observations` (filtros e paginação) e `GET /api/data/observations/series`. Os dados ainda não são exibidos na interface.

## Histórico local

Cada consulta bem-sucedida na página **Mercado** registra um snapshot em `data/portfolio_history.db`, um banco SQLite local ignorado pelo Git. A página **Histórico** mostra a evolução dos valores e das posições. Ela não calcula retorno TWR, XIRR ou rentabilidade total: para isso também é necessário registrar cada aporte, retirada, imposto e provento.

## Testes

```bash
pytest                  # backend: domínio, API e persistência
cd frontend && npm test # frontend: Vitest + Testing Library
```

## Arquitetura e roadmap

A visão arquitetural, decisões técnicas e fases de implementação estão documentadas em [`docs/architecture/`](docs/architecture/README.md) e no [roadmap](docs/architecture/implementation-roadmap.md).
