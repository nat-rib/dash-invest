# Roadmap: migração das telas para React + FastAPI

**Status:** migração concluída — fases 0 a 6 implementadas em React + FastAPI, publicadas em produção e Streamlit removido. Pendências: validação user-facing e testes automatizados do frontend.  
**Branch de referência:** `develop` (integração) → `main` (produção)  
**Última atualização:** 08/11/2026  
**Objetivo:** migrar todas as funcionalidades da interface Streamlit para React + TypeScript, mantendo as regras de negócio e cálculos financeiros no backend Python.

## 1. Princípios de arquitetura

- React + TypeScript é responsável pela interface e experiência de uso.
- FastAPI expõe contratos HTTP validados com Pydantic.
- Regras financeiras permanecem nos módulos Python existentes (`src/domain`, `src/persistence`, `src/importers`, `src/mortgage` etc.).
- SQLite permanece como fonte oficial do ledger.
- Snapshot JSON, ledger transacional e histórico de cotações são fontes distintas; não inferir transações ou rentabilidade a partir de snapshots isolados.
- Operações de escrita devem ter validação, confirmação explícita e persistência atômica quando aplicável.
- Dados financeiros, arquivos e credenciais não devem ser enviados a provedores externos sem necessidade e consentimento.
- Preservar a implantação em um único container: frontend compilado no estágio Node e servido pelo FastAPI no runtime Python.

## 2. Estrutura alvo

```text
api/
  main.py
  routes/
    overview.py
    portfolio.py
    ledger.py
    performance.py
    imports.py
    analysis.py
    history.py
    market.py
    mortgage.py
  schemas/
  services/

frontend/src/
  components/
  layouts/
  pages/
  services/
  hooks/
  types/
```

A estrutura é uma proposta de organização. Antes de criar módulos, verificar o código existente e reutilizar serviços e repositórios; evitar duplicar lógica.

## 3. Fases de implementação

> **Progresso (08/11/2026):** todas as fases 0 a 6 estão implementadas e em produção.
>
> - **Fase 0:** `api/` com FastAPI, schemas Pydantic, camada de serviços, healthcheck e OpenAPI; esqueleto React em `frontend/`.
> - **Fase 1:** ledger completo (`transactions`, `instruments`, `snapshot/preview|import`, `csv/preview|import`, `transfers/suggestions|confirm`, `state`) e tela `LedgerPage.tsx`.
> - **Fase 2:** fluxos, XIRR, TWR e avaliações (`/api/performance/*`) e `PerformancePage.tsx`.
> - **Fase 3:** prévia e confirmação de substituição do snapshot em `ImportPage.tsx`.
> - **Fase 4:** alocação, concentração e detalhes do ativo em `AnalysisPage.tsx`.
> - **Fase 5:** histórico patrimonial e cotações (`HistoricoPage.tsx`, `MercadoPage.tsx`).
> - **Fase 6:** simulador SAC e comparação com investimento em `AmortizacaoPage.tsx`.
>
> A migração do snapshot permanece idempotente, a prévia de CSV não persiste e nenhuma conciliação acontece sem confirmação.

### Fase 0 — Fundação da API e contratos

**Escopo**
- Separar rotas por domínio e centralizar inicialização/acesso ao banco.
- Definir schemas Pydantic de request/response.
- Padronizar paginação, filtros, erros e validações.
- Criar camada de serviços entre rotas e domínio/repositórios.
- Organizar no frontend os serviços HTTP, tipos, componentes reutilizáveis e estados de loading/erro/vazio.
- Implementar navegação/rotas reais sem remover funcionalidades existentes prematuramente.

**Critérios de aceite**
- Endpoints documentados no OpenAPI.
- Testes unitários e de integração para os contratos.
- Nenhuma regra financeira duplicada no frontend.
- Build TypeScript/Vite e testes Python passando.

### Fase 1 — Ledger e operações

**Tela de origem:** `pages/8_Ledger.py`

**Funcionalidades**
- Listagem de transações com paginação e filtros por data, ativo, instituição e tipo.
- Consulta e cadastro de instrumentos.
- Prévia e migração do snapshot legado para SQLite.
- Upload, leitura, mapeamento e prévia de CSV de corretoras.
- Validação de linhas, detecção de duplicidades e importação idempotente.
- Sugestões e conciliação manual de transferências.
- Estado do banco e informações úteis de auditoria.

**Endpoints propostos**
- `GET /api/ledger/transactions`
- `GET /api/ledger/instruments`
- `POST /api/ledger/instruments`
- `POST /api/ledger/snapshot/preview`
- `POST /api/ledger/snapshot/import`
- `POST /api/ledger/csv/preview`
- `POST /api/ledger/csv/import`
- `GET /api/ledger/transfers/suggestions`
- `POST /api/ledger/transfers/confirm`

**Critérios de aceite**
- Importação idempotente e validada antes da persistência.
- Prévia disponível antes de confirmar operações.
- Migração de snapshot não cria transações fictícias e preserva o JSON original.
- Transferências não são conciliadas automaticamente sem confirmação.
- Erros por linha e resultado da importação são apresentados claramente.

### Fase 2 — Rentabilidade

**Tela de origem:** `pages/9_Rentabilidade.py`

**Funcionalidades**
- Listagem dos fluxos externos identificados no ledger.
- Cálculo de XIRR com valor terminal e data de avaliação.
- Cadastro de avaliações/períodos para cálculo de TWR.
- Exibição dos períodos considerados, datas, moeda-base e resultados.
- Explicação de limitações e dados faltantes.

**Endpoints propostos**
- `GET /api/performance/flows`
- `POST /api/performance/xirr/calculate`
- `GET /api/performance/twr`
- `POST /api/performance/twr/calculate`
- `POST /api/performance/valuations`

**Critérios de aceite**
- Reutilizar `src.domain.performance` e comparar resultados com testes de regressão.
- Respeitar sinais, datas reais, moeda-base e convenção anual já adotada.
- Não inferir TWR de snapshots isolados nem estimar cotações/avaliações ausentes.
- Exibir claramente quando o cálculo for indisponível e por quê.

### Fase 3 — Importação de carteira

**Tela de origem:** `pages/3_Importacao.py`

**Funcionalidades**
- Upload de `portfolio.json`.
- Validação de schema e mensagens de erro acionáveis.
- Detecção de possíveis posições duplicadas.
- Prévia dos dados interpretados.
- Confirmação explícita para substituir o snapshot atual.

**Endpoints propostos**
- `POST /api/import/snapshot/preview`
- `POST /api/import/snapshot/confirm`

**Critérios de aceite**
- Arquivo inválido nunca substitui o snapshot atual.
- Usuário visualiza a prévia e confirma a substituição.
- Escrita atômica e preservação/recuperação do arquivo anterior em caso de falha.
- Reutilizar as funções existentes de validação e substituição.

### Fase 4 — Análise e detalhes dos ativos

**Telas de origem:** `pages/2_Analise.py` e `pages/4_Detalhes.py`

**Análise**
- Distribuição por classe e instituição.
- Concentração por ativo e maiores posições.
- Comparação entre custo de aquisição e valor atual quando comparáveis.
- Filtros por classe/instituição quando fizerem sentido para os dados.

**Detalhes**
- Quantidade, preço médio, preço atual, custo total e valor atual.
- Ganho/perda e rentabilidade não realizados.
- Moeda, indexador, vencimento, emissor, liquidez, risco e demais atributos disponíveis.
- Tratamento explícito de campos ausentes.

**Endpoints propostos**
- `GET /api/analysis/allocation`
- `GET /api/analysis/concentration`
- `GET /api/analysis/institutions`
- `GET /api/portfolio/positions/{position_id}`

**Critérios de aceite**
- Valores e percentuais coerentes com os módulos Python existentes.
- Não converter ausência de informação em zero.
- Seleção e filtros funcionais; tabelas e gráficos responsivos.

### Fase 5 — Histórico e mercado

**Telas de origem:** `pages/7_Historico.py` e `pages/6_Mercado.py`

**Histórico**
- Evolução do patrimônio consolidado.
- Evolução individual de posições.
- Comparação de snapshots e identificação da origem/data-base.
- Aviso claro de que variação patrimonial não equivale a rentabilidade.

**Mercado**
- Consulta de histórico diário e cotações.
- Conversão cambial quando suportada.
- Prévia de atualização de preços e confirmação antes de alterar o snapshot.
- Tratamento de limites, indisponibilidade e erros do provedor.

**Endpoints propostos**
- `GET /api/history/portfolio`
- `GET /api/history/positions/{position_id}`
- `GET /api/market/quotes`
- `GET /api/market/history/{symbol}`
- `POST /api/market/quotes/preview`
- `POST /api/market/quotes/confirm`

**Critérios de aceite**
- Verificar e garantir persistência do histórico no volume da VPS; revisar o caminho atual `data/portfolio_history.db`.
- Evitar snapshots duplicados e preservar a origem de cada registro.
- Respeitar limites do provedor e não expor chaves no frontend.
- Nenhuma cotação é aplicada sem prévia e confirmação.
- Dados de carteira não são enviados ao provedor; enviar apenas símbolos necessários.

### Fase 6 — Amortização ou investimento

**Tela de origem:** `pages/5_Amortizacao.py`

**Funcionalidades**
- Parâmetros do financiamento SAC: saldo, prazo, juros, TR estimada, seguros e taxas.
- Simulação de amortização reduzindo prazo ou parcela.
- Comparação com investimento sob retorno líquido informado.
- Taxa líquida de equilíbrio.
- Gráfico de saldo devedor e tabelas de parcelas.

**Endpoints propostos**
- `POST /api/mortgage/simulate`
- `POST /api/mortgage/compare`

**Critérios de aceite**
- Reutilizar `src.mortgage` e validar paridade dos resultados.
- Premissas, cenários e limitações visíveis.
- Simulação não executa nenhuma operação bancária real.

## 4. Sequência de PRs sugerida

> Todas as entregas abaixo foram concluídas até 08/11/2026; a tabela permanece como registro do sequenciamento original.

| PR | Escopo | Resultado esperado |
|---|---|---|
| 1 | Fundação da API e contratos | Estrutura modular, schemas e testes |
| 2 | Ledger | Operações, importação CSV, migração e conciliação |
| 3 | Rentabilidade | Fluxos, XIRR, TWR e avaliações |
| 4 | Importação de carteira | Preview e substituição segura do snapshot |
| 5 | Análise e detalhes | Consultas, gráficos e detalhes dos ativos |
| 6 | Histórico e mercado | Série histórica, cotações e atualização confirmada |
| 7 | Amortização | Simulador SAC e comparação |

Cada PR deve ser pequeno o suficiente para revisão, manter a aplicação implantável e incluir backend, frontend, testes e documentação da funcionalidade correspondente.

## 5. Requisitos transversais

- **Segurança:** manter a API no ambiente privado atual; validar uploads e entradas; nunca expor segredos no bundle frontend.
- **Persistência:** SQLite, snapshots e históricos em volumes persistentes; backups antes de migrações destrutivas.
- **Integridade:** transações atômicas, idempotência e prevenção de duplicidades.
- **Observabilidade:** logs estruturados, erros rastreáveis e healthcheck.
- **Performance:** paginação e filtros no backend; evitar carregar todo o ledger de uma vez.
- **UX:** responsividade desktop/mobile, acessibilidade básica e estados de loading/erro/vazio.
- **Qualidade:** testes unitários, integração, regressão financeira e build frontend.
- **Deploy:** pipeline existente, validação pós-deploy e estratégia de rollback sem perda de dados.

## 6. Definição de concluído

- [x] Todas as telas e funcionalidades existentes foram migradas para React (9 páginas em `frontend/src/pages/`).
- [x] Nenhuma regra financeira foi duplicada no frontend: XIRR, TWR, alocação e reconstrução vêm da API; a UI apenas formata.
- [x] Cálculos financeiros passaram por testes de regressão (`tests/test_performance.py`, `tests/test_mortgage.py`, `tests/test_ledger_reconstruction.py`).
- [x] Importações e operações de escrita são validadas e seguras (prévia + confirmação, persistência atômica e idempotente).
- [x] Ledger, snapshots e histórico persistem após recriação do container (volume em `/app/data`, validado no deploy de 08/11/2026).
- [x] Interface validada em desktop e dispositivos móveis de forma **automatizada** (overflow em 360 px, 390 px, 430 px e desktop).
- [ ] Validação user-facing em dispositivos reais.
- [x] Documentação e OpenAPI atualizados.
- [x] Todas as funcionalidades necessárias operam sem depender do Streamlit.
- [ ] Testes automatizados de frontend (Vitest + Playwright).
- [x] Streamlit removido após confirmar paridade funcional e operacional.

> A paridade funcional foi confirmada e o Streamlit foi removido em 08/11/2026; a aplicação opera somente com React + FastAPI.

## 7. Próximos passos

1. Validação user-facing das telas migradas em desktop e celular.
2. Adicionar testes automatizados de frontend (Vitest para unidades, Playwright para fluxos).
3. Retomar a evolução do produto pela Fase 3 (data platform) de [`architecture/implementation-roadmap.md`](architecture/implementation-roadmap.md).
