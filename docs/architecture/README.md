# Dash-Invest — arquitetura

> Documento vivo: descreve o destino arquitetural; nem todos os módulos estão implementados.

## Objetivo

Evoluir o dashboard pessoal para uma plataforma privada de inteligência de investimentos, cobrindo múltiplas classes de ativos, acompanhamento de carteira, análise quantitativa, descoberta de oportunidades e pesquisa assistida por IA.

## Princípios

1. Números determinísticos, interpretação assistida: fórmulas financeiras são implementadas e testadas em Python; LLMs explicam evidências, nunca substituem cálculos.
2. Ledger como fonte da verdade: transações e eventos corporativos formam a história econômica; posições e snapshots são projeções.
3. Instrumento não é posição: identidade do ativo independe da corretora, carteira, ticker e quantidade.
4. Moeda explícita: não converter sem taxa, data e fonte identificáveis.
5. Ausência não é zero: dados ausentes, desatualizados ou não aplicáveis permanecem explícitos.
6. Rastreabilidade: dados externos guardam provedor, instante de coleta, data de referência/publicação e qualidade.
7. Privacidade por padrão: carteira, transações, credenciais e documentos privados ficam fora do Git e da imagem Docker; acesso permanece na tailnet.
8. Evolução incremental: preservar Streamlit e o funcionamento atual enquanto novos domínios são introduzidos por contratos testáveis.

## Visão de produto

- Portfolio: posições, transações, proventos, rentabilidade, alocação e instituições.
- Discovery: screener, filtros e oportunidades.
- Analytics: risco, retorno, correlação, cenários e contribuição ao risco.
- Fundamentals: demonstrações financeiras, indicadores e valuation.
- AI Research: pesquisa documental com evidências, citações e limitações.
- Mobile Experience: navegação responsiva e fluxos otimizados para celular.

## Arquitetura lógica

    flowchart TB
      UI[Streamlit UI / páginas responsivas]
      APP[Application services]
      DOMAIN[Domain: instrumentos, ledger, carteira]
      ANALYTICS[Analytics: retorno, risco, valuation]
      PROVIDERS[Provider adapters]
      INGEST[Ingestion + data quality]
      AI[LLM Gateway + Research]
      SQLITE[(SQLite operacional)]
      DUCK[(DuckDB analítico)]
      PARQUET[(Parquet histórico)]
      DOCS[(Documentos / cache)]
      UI --> APP
      APP --> DOMAIN
      APP --> ANALYTICS
      APP --> AI
      APP --> SQLITE
      ANALYTICS --> DUCK
      ANALYTICS --> PARQUET
      INGEST --> PROVIDERS
      INGEST --> SQLITE
      INGEST --> PARQUET
      AI --> DOCS
      AI --> PROVIDERS

### Camadas e responsabilidades

| Camada | Responsabilidade | Regra |
|---|---|---|
| UI | Streamlit, navegação, componentes e visualizações | Não contém regra financeira |
| Application | Casos de uso e coordenação | Orquestra domínio, repositórios e provedores |
| Domain | Instrumentos, carteiras, transações e invariantes | Independente de Streamlit, SQLite e APIs |
| Analytics | Fórmulas de retorno, risco, fundamentos e valuation | Determinístico, com unidades/frequências explícitas |
| Providers | Adaptadores de mercado, macro, fundamentos e documentos | Contratos independentes do fornecedor |
| Ingestion | Coleta, normalização, validação e histórico | Idempotente e auditável |
| AI | Gateway, retrieval e agentes de pesquisa | LLM interpreta evidência; não é fonte de números |
| Persistence | SQLite, DuckDB, Parquet e documentos | Repositórios isolam armazenamento |

## Stack alvo

| Área | Escolha inicial |
|---|---|
| Linguagem | Python 3.11+ (runtime atual); alvo Python 3.12+ |
| UI | Streamlit |
| Contratos | Pydantic 2 |
| Operacional | SQLite com WAL e migrations versionadas |
| Analytics | DuckDB + Pandas/NumPy |
| Histórico volumoso | Parquet |
| Gráficos | Plotly |
| Testes | Pytest |
| Jobs | systemd timers / jobs simples |
| Deploy | Docker Compose + GHCR + Tailscale Serve |

Não introduzir PostgreSQL, Redis, Kafka ou Airflow agora: uso individual e recursos da VPS não justificam a complexidade operacional.

## Modelo de domínio

### Instrument

Identidade estável e global do ativo. ID interno é a chave; ticker é identificador externo mutável e dependente de bolsa/provedor. Campos: id, name, asset_class, subclass, currency, country, exchange, issuer_id, provider_symbols e metadata.

### Portfolio e PortfolioPosition

Uma carteira pode deter instrumentos em instituições diferentes. A posição é uma projeção de quantidade e custo médio, derivada do ledger ou reconciliada com posição importada. Não confundir posição com cadastro do instrumento.

### Transaction / ledger

Eventos com data/hora, sequência explícita para desempate no mesmo instante, carteira, instrumento (quando aplicável), instituição, tipo, quantidade, preço unitário, valor, moeda, taxas, impostos e referência de transferência. Correções devem gerar estorno/novo evento auditável, não apagar o histórico.

Tipos previstos: BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, JCP, INTEREST, COUPON, AMORTIZATION, TAX, FEE, SPLIT, BONUS, TRANSFER_IN e TRANSFER_OUT.

Transferências entre instituições precisam compartilhar uma referência e não podem ser classificadas como aporte ou retirada externa. Eventos corporativos têm semântica própria para não distorcer custo ou rentabilidade.

### Snapshots

Snapshots são materializações para leitura rápida, não origem da verdade. Guardam timestamp e versão do cálculo. O histórico legado não deve ser interpretado como ledger nem usado para inventar fluxos ausentes.

## Suporte por classe

| Classe | Dados e análises principais |
|---|---|
| Ações | DRE, balanço, fluxo de caixa, margens, ROE/ROIC, dívida, FCF, dividendos e valuation |
| FIIs | P/VP, patrimônio, vacância, rendimentos, imóveis, devedores e concentração |
| ETFs | Taxas, benchmark, tracking error, composição e exposição look-through |
| Fundos | PL, benchmark, taxas, liquidez, estratégia, gestor e composição disponível |
| Renda fixa | Emissor, indexador, taxa, vencimento, duration, crédito, liquidez e fluxos |
| Exterior / REITs | Fundamentos, moeda, país, bolsa, tributação e métricas do mercado de origem |
| Cripto | Preço, volatilidade, drawdown, liquidez, concentração e métricas on-chain confiáveis |

Não criar score universal comparando diretamente classes com naturezas diferentes. Separar qualidade do ativo, adequação à carteira e confiança dos dados.

## Data platform e proveniência

Cada observação externa deve preservar, quando disponível: provider, instrument_id, metric, value, currency, unit, period_start, period_end, reference_date, published_at, collected_at, parser_version e quality_status.

Provedores são encapsulados em interfaces como MarketDataProvider, FundamentalsProvider, MacroDataProvider e DocumentsProvider. Fontes candidatas: CVM (DFP/ITR), SEC EDGAR/XBRL, Banco Central, provedores de preços e documentos oficiais de emissores/administradores. Licenças e limites devem ser verificados antes de cada integração.

Regras de qualidade: preço positivo; moeda explícita; datas sem duplicidade; unidade e período explícitos; reapresentações preservadas; ausência nunca convertida em zero; cotação com idade visível; histórico insuficiente não gera estatística artificial.

## Engines quantitativos

- Fundamentals: métricas por setor; bancos e seguradoras exigem modelos próprios.
- Valuation: DCF, múltiplos, dividend discount, P/VP, fluxo de rendimentos e desconto de fluxos de renda fixa, conforme aplicabilidade. Cenários pessimista/base/otimista com premissas explícitas e editáveis.
- Risk: volatilidade, drawdown, beta, Sharpe, Sortino, VaR/CVaR, correlação, risco cambial; duration e risco de crédito para renda fixa. VaR não é perda máxima garantida.
- Portfolio Fit: concentração, exposição setorial/cambial, correlação, liquidez, crédito e contribuição marginal ao risco.

Frequência, janela, moeda e benchmark acompanham cada métrica. Sharpe em BRL não pode usar taxa livre de risco em USD sem metodologia explícita.

## IA híbrida e pesquisa

O LLM Gateway abstrai provedores, modelos, custo/tokens, timeout, retry e cache. O Research Agent segue: identificar ativo → buscar dados estruturados → obter documentos → executar cálculos Python → pedir interpretação ao LLM → validar citações → emitir relatório.

Saída estruturada: claim, evidence, source_urls, publication_dates, confidence e limitations. Começar com SQLite FTS5 e busca textual; embeddings só quando houver necessidade demonstrada. Documentos externos são dados não confiáveis, nunca instruções. Não enviar o JSON completo da carteira ao LLM; transmitir somente contexto mínimo e autorizado.

## Segurança e operação

- Dados financeiros reais, banco local, secrets e backups nunca entram no Git ou na imagem.
- Aplicação acessível somente via Tailscale Serve; bind em 127.0.0.1; sem Funnel e sem porta pública.
- Container não-root, filesystem read-only quando possível e volume persistente fora do código.
- Backups consistentes do SQLite e arquivos, com retenção e teste de restauração.
- Logs sem saldos, tokens ou dados pessoais desnecessários.

## Estrutura alvo (criar sob demanda)

    src/
      domain/          # instrumentos, portfolio, transactions, enums
      application/     # portfolio, screener, research e opportunity services
      analytics/       # returns, risk, valuation, fundamentals, portfolio_fit
      providers/       # market, fundamentals, macro, documents, crypto
      ai/              # gateway, research agent, schemas e retrieval
      ingestion/       # pipelines, normalization e quality
      persistence/     # sqlite, duckdb e repositories
      ui/              # components, layouts e formatting
    jobs/
    docs/architecture/
    tests/

Os diretórios são criados conforme cada fase for implementada, evitando scaffolding vazio.
