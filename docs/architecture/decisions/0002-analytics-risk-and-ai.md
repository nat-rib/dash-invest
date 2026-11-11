# ADR 0002 — Analítica, risco e IA (Fases 4–7)

**Status:** aceito em 10/11/2026.

## Contexto

As fases 4 a 7 do roadmap exigiam risco, screener/valuation, portfolio fit e
pesquisa assistida por IA. O produto é de uso individual, roda em um container
com 768 MiB e já mantém ledger, snapshots e observações externas com
proveniência.

## Decisões

1. **Métricas determinísticas em Python.** Risco, razões fundamentalistas e DCF
   vivem em `src/analytics/` e são testados com séries sintéticas. Nenhum
   cálculo é feito no frontend.
2. **Ausência não é zero.** Amostra insuficiente, denominador inválido ou dado
   faltante retornam `null` e uma lista explícita de indisponibilidade. O DCF só
   aceita premissas informadas e valida desconto > perpetuidade.
3. **Preços como observações.** Séries diárias entram em `observations` com
   provider `csv` ou `alpha_vantage`, métrica `close`, `reference_date` e link
   de origem. O motor de risco lê essas séries; não há scraping nem preço
   inventado.
4. **Risco da carteira pelo histórico real.** Usa os snapshots de
   `portfolio_history.db`; se houver menos de 20 retornos, as métricas
   anualizadas ficam indisponíveis.
5. **Screener restrito à CVM.** Usa as últimas observações anuais (`cvm`) e
   cruza com os emissores por CNPJ. Comparação setorial, múltiplos e cenários
   ficam pendentes de dados de setor e de ações em circulação.
6. **Portfolio Fit declara limitações.** Look-through de ETFs, setor e duration
   de renda fixa não são inferidos; aparecem como indisponíveis.
7. **IA é opcional e subordinada aos fatos.** O `NarrativeGateway` só redige.
   O prompt recebe exclusivamente claims calculados, com data e fonte; o LLM é
   proibido de inventar números. Sem `AI_BASE_URL`/`AI_API_KEY`, a narrativa é
   determinística e nenhum dado sai da VPS.
8. **Privacidade.** O relatório envia apenas dados públicos do emissor
   escolhido, nunca a carteira completa.

## Adiado com justificativa

- **SEC EDGAR/XBRL:** sem instrumentos americanos na carteira atual; a
  implementação exige mapeamento de conceitos us-gaap e respeito ao rate limit
  da SEC. O modelo de `Observation` já suporta o provider.
- **Parquet + DuckDB:** ~450 mil linhas cabem no SQLite e as consultas atuais
  são por série/emissor. A camada analítica só se justifica com ingestão
  histórica massiva.
- **FTS5 de documentos:** o relatório cita links oficiais; armazenar e indexar
  o texto integral dos PDFs é o próximo passo para retrieval de verdade.
- **Cache/retries do gateway:** o timeout já existe; cache e retry entram
  quando houver uso recorrente de LLM.

## Consequências

- O sistema permanece implantável em um container e sem dependências novas
  pesadas.
- Toda métrica é reproduzível e rastreável; limitações são visíveis na UI.
- As pendências estão registradas no roadmap e podem ser retomadas sem
  refatoração estrutural.
