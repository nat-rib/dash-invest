# Roadmap de implementação

Roadmap incremental e orientado a entregas verificáveis. Estimativas representam esforço individual, não datas prometidas. Duas trilhas coordenadas: inteligência de investimentos e experiência mobile.

## Fase 0 — Preparação e governança

**Estimativa:** 2–3 dias.

- [x] Definir arquitetura alvo e princípios.
- [x] Documentar fases, riscos e critérios de aceite.
- [ ] Finalizar revisão do PR de CI/CD existente.
- [ ] Registrar ADRs para decisões estruturais.
- [ ] Definir convenções de branch, migração e testes financeiros.

**Aceite:** documentação versionada; develop como integração; main somente produção; CI executa testes em PR; nenhum dado pessoal no repositório.

## Fase 1 — Mobile redesign e navegação

**Estimativa:** 4–6 dias.

- [ ] Reorganizar navegação em Visão geral, Minha carteira, Investigar, Mercado e Configurações.
- [ ] Dashboard com patrimônio, rentabilidade disponível, benchmark, alocação, maiores posições e alertas.
- [ ] Componentes reutilizáveis: metric_card, position_card, opportunity_card, risk_badge, responsive_chart e indicador de qualidade.
- [ ] Transformar tabelas extensas em cards no celular; preservar tabelas completas no desktop.
- [ ] Validar em 390 px, 430 px, desktop e Android S23.
- [ ] Evitar rolagem horizontal e controles pequenos.

**Aceite:** fluxos principais utilizáveis em celular sem scroll horizontal; desktop continua funcional; nenhuma fórmula financeira duplicada na UI.

## Fase 2 — Portfolio Engine e ledger

**Estimativa:** 1–2 semanas.

- [x] Introduzir modelos iniciais de Instrument, Portfolio, PortfolioPosition e Transaction.
- [ ] Persistência SQLite versionada e repositórios.
- [ ] Migração do snapshot JSON para cadastro/posições sem perder compatibilidade.
- [ ] Importação e reconciliação de transações.
- [ ] Eventos de proventos, juros, amortizações, splits, bonificações e transferências.
- [ ] Reconstrução de posições e custo a partir do ledger.
- [ ] Cálculo TWR e XIRR após validação dos fluxos.

**Aceite:** transferências internas não alteram aportes/retiradas externos; proventos não duplicam; splits preservam valor econômico; TWR trata fluxos externos; XIRR usa datas reais; snapshots legados não viram transações fictícias.

## Fase 3 — Data platform e fundamentos

**Estimativa:** 1–2 semanas.

- [ ] Interfaces para preços, fundamentos, macro e documentos.
- [ ] Ingestão inicial CVM DFP/ITR e normalização.
- [ ] Persistir dados brutos e normalizados com proveniência.
- [ ] Parquet para séries; DuckDB para consultas analíticas.
- [ ] Controles de qualidade, reapresentações e atualização.
- [ ] SEC EDGAR/XBRL como fonte para empresas americanas.

**Aceite:** pipelines idempotentes; cada número rastreável até provedor e data; ausências preservadas; reapresentações não sobrescrevem silenciosamente a história.

## Fase 4 — Risk Engine

**Estimativa:** 1 semana.

- [ ] Retorno diário e mensal por instrumento e carteira.
- [ ] Volatilidade, drawdown, beta, Sharpe e Sortino.
- [ ] VaR/CVaR histórico e paramétrico.
- [ ] Correlação e concentração por setor, moeda e classe.
- [ ] Duration, sensibilidade a juros e indicadores de crédito para renda fixa.

**Aceite:** testes com séries sintéticas conhecidas; frequência e moeda explícitas; amostra insuficiente retorna indisponível, não zero ou estimativa fabricada.

## Fase 5 — Screener e valuation

**Estimativa:** 2 semanas.

- [ ] Screener inicial de ações brasileiras.
- [ ] Indicadores fundamentalistas e comparação setorial.
- [ ] Valuation DCF e múltiplos com premissas visíveis.
- [ ] Cenários pessimista/base/otimista e análise de sensibilidade.
- [ ] Explicação dos filtros e qualidade/cobertura dos dados.

**Aceite:** resultados reproduzíveis; nenhuma recomendação baseada em dado ausente; preço-alvo acompanhado de premissas e cenários.

## Fase 6 — Portfolio Fit e multiativos

**Estimativa:** 2 semanas.

- [ ] Concentração, correlação, exposição cambial e liquidez.
- [ ] ETFs com look-through quando composição estiver disponível.
- [ ] Modelos específicos para FIIs, fundos e renda fixa.
- [ ] Cobertura de REITs, ações internacionais e cripto.
- [ ] Separar qualidade do ativo, adequação à carteira e confiança dos dados.

**Aceite:** métricas específicas por classe; nenhum score universal enganoso; exposição desconhecida permanece desconhecida.

## Fase 7 — AI Research

**Estimativa:** 1–2 semanas.

- [ ] LLM Gateway independente de provedor.
- [ ] Retrieval de documentos oficiais com FTS5 inicialmente.
- [ ] Research Agent com fluxo dados → documentos → cálculos → interpretação.
- [ ] Relatórios com claims, evidências, URLs, datas e limitações.
- [ ] Controles de custo, cache, timeouts, retries e privacidade.

**Aceite:** afirmações factuais relevantes têm evidência; IA não calcula indicadores nem inventa valores; admite falta de dados; carteira privada não é enviada integralmente.

## Sequenciamento e dependências

    flowchart TD
      P0[Fase 0: governança] --> P1[Fase 1: mobile]
      P0 --> P2[Fase 2: ledger]
      P2 --> P3[Fase 3: data platform]
      P2 --> P4[Fase 4: risco]
      P3 --> P5[Fase 5: screener e valuation]
      P4 --> P6[Fase 6: portfolio fit]
      P5 --> P6
      P3 --> P7[Fase 7: AI Research]
      P5 --> P7

Mobile pode avançar em paralelo com domínio, mas não deve introduzir cálculos independentes. AI Research depende de dados e documentos rastreáveis.

## Qualidade e testes transversais

- Unit tests para fórmulas, arredondamento, moedas, datas e invariantes de domínio.
- Integration tests para SQLite, migrations e adapters.
- Regressão financeira com casos de resultado esperado.
- Testes de interface desktop/mobile.
- Casos obrigatórios: aporte intermediário, retirada, transferência entre corretoras, dividendos, JCP, juros, amortização, split, bonificação, câmbio, reapresentação de demonstrações e dados ausentes.
- IA avaliada por fidelidade, citações, data de publicação e capacidade de declarar incerteza.

## Regras de entrega

- Branch curta a partir de develop; PR pequeno e descritivo.
- Não fazer deploy de develop; produção somente após merge em main.
- Cada fase entrega código, testes, documentação e migração quando aplicável.
- Não quebrar importação JSON existente até existir migração explícita e testada.
