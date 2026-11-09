# Roadmap de implementação

Roadmap incremental e orientado a entregas verificáveis. Estimativas representam esforço individual, não datas prometidas. Duas trilhas coordenadas: inteligência de investimentos e experiência mobile.

## Fase 0 — Preparação e governança

**Estimativa:** 2–3 dias.

- [x] Definir arquitetura alvo e princípios.
- [x] Documentar fases, riscos e critérios de aceite.
- [x] Finalizar revisão do PR de CI/CD existente.
- [x] Registrar ADRs para decisões estruturais.
- [x] Definir convenções de branch, migração e testes financeiros.

**Aceite:** documentação versionada; develop como integração; main somente produção; CI executa testes em PR; nenhum dado pessoal no repositório. Governança e CI/CD foram concluídos; deploy privado em produção validado em 04/11/2026.

## Fase 1 — Mobile redesign e navegação

**Estimativa:** 4–6 dias.

- [x] Reorganizar navegação em Visão geral, Minha carteira, Investigar, Mercado e Configurações.
- [x] Dashboard com patrimônio, rentabilidade disponível, benchmark, alocação, maiores posições e alertas.
- [x] Componentes reutilizáveis: metric_card, position_card, opportunity_card, risk_badge, responsive_chart e indicador de qualidade.
- [x] Transformar tabelas extensas em cards no celular; preservar tabelas completas no desktop.
- [x] Validar em 390 px, 430 px, desktop e Android S23.
- [x] Evitar rolagem horizontal e controles pequenos.

**Estado:** navegação agrupada e dashboard consolidado implementados. O endpoint `GET /api/overview` reúne snapshot, cobertura, alocação, maiores posições, alertas, disponibilidade de TWR, benchmark e estado do ledger, sem combinar fontes silenciosamente. Componentes reutilizáveis foram extraídos para `frontend/src/components/insights.tsx`; tabelas largas viram cartões no celular e permanecem tabelas no desktop. A validação automatizada de overflow cobre 360 px, 390 px, 430 px e desktop; Android S23 usa o viewport de 360 px. Benchmark continua explicitamente não configurado, e TWR/XIRR dependem de fluxos e avaliações reais.

**Aceite:** fluxos principais utilizáveis em celular sem scroll horizontal; desktop continua funcional; nenhuma fórmula financeira duplicada na UI.

## Fase 2 — Portfolio Engine e ledger

**Estimativa:** 1–2 semanas.

- [x] Introduzir modelos de Instrument, Portfolio, PortfolioPosition e Transaction.
- [x] Persistência SQLite versionada, repositórios e ledger append-only.
- [x] Importação de snapshot JSON para cadastro/posições, repetível e sem fabricar transações.
- [x] Tela de migração explícita: preserva o JSON original e grava o snapshot no SQLite.
- [x] Importação canônica CSV idempotente, com validação completa e persistência atômica.
- [x] Adaptador CSV configurável para layouts distintos de bancos/corretoras, com mapeamento de colunas, tipos em português, timezone, locale decimal e resolução do ativo no catálogo.
- [x] Tela de importação de extratos na interface.
- [x] Sugestão conservadora e confirmação manual de transferências; vínculos ficam em tabela separada, sem editar eventos do ledger.
- [x] Eventos de proventos, JCP, juros, cupons, amortizações, taxas, impostos, splits, bonificações e transferências.
- [x] Reconstrução de posições e custo para compras, vendas, transferências de ativos, splits, bonificações e amortizações.
- [x] Cálculo TWR por subperíodos com fluxos externos delimitados.
- [x] Cálculo XIRR com datas reais, base anual de 365 dias e detecção conservadora de fluxos ambíguos.
- [x] Interface para revisar fluxos, calcular XIRR e informar avaliações para TWR.

**Limites conhecidos:** o adaptador é configurável, não um parser proprietário pré-configurado para cada instituição; o usuário mapeia o layout no upload. IDs externos sintéticos são usados apenas quando o extrato não fornece identificador estável, com fingerprint do conteúdo e ordinal de repetição. TWR depende de avaliações reais nos limites dos fluxos; o app não estima preços ausentes. Operações em moedas diferentes exigem conversão cambial explícita.

**Aceite:** transferências internas não alteram aportes/retiradas externos; proventos não duplicam; splits preservam valor econômico; TWR trata fluxos externos; XIRR usa datas reais; snapshots legados não viram transações fictícias.

## Fase 3 — Data platform e fundamentos

**Estimativa:** 1–2 semanas.

- [x] Interfaces para preços, fundamentos, macro e documentos (`src/providers/base.py`).
- [ ] Ingestão inicial CVM DFP/ITR e normalização. **DFP entregue; ITR pendente.**
- [x] Persistir dados brutos e normalizados com proveniência.
- [ ] Parquet para séries; DuckDB para consultas analíticas.
- [ ] Controles de qualidade, reapresentações e atualização.
- [ ] SEC EDGAR/XBRL como fonte para empresas americanas.

**Estado (09/11/2026):** fundação de proveniência e primeiro provedor entregues.
- `Observation` (`src/domain/observations.py`), tabela `observations` (migration `0005`) e repositório append-only com supersessão (`src/persistence/observations.py`); inserção em lote por transação.
- Interfaces de provedores em `src/providers/base.py`.
- Adaptador **CVM DFP** em `src/providers/cvm.py`: download do ZIP anual, índice de documentos (`DT_RECEB`/link), normalização de escala (`MIL` → unidades) e descarte do exercício comparativo (`PENÚLTIMO`).
- Job: `python -m jobs.ingest_cvm --year 2024 [--individual]`.
- Leitura: `GET /api/data/observations` (filtros + paginação) e `GET /api/data/observations/series`.
- Validação com o arquivo real de 2024: 16.388 observações consolidadas do DRE, todas com `published_at`, link do documento e moeda BRL; 1.869 métricas canônicas.
- Pendentes: ITR, Parquet/DuckDB, SEC e exposição na interface.

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
