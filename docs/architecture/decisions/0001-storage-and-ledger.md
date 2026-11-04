# ADR 0001 — SQLite operacional e ledger como fonte da verdade

- **Status:** Aceito
- **Data:** 2026-11-04

## Contexto

O Dash-Invest é uma aplicação individual em uma VPS pequena. O estado atual usa snapshots JSON e histórico SQLite. A expansão exige transações, instrumentos, eventos corporativos, consultas históricas e cálculos de rentabilidade, sem justificar infraestrutura distribuída.

## Decisão

1. SQLite será o armazenamento operacional inicial, com WAL, transações curtas e migrations versionadas.
2. Um ledger de transações/eventos será a fonte da verdade para reconstrução de posições e fluxos de caixa.
3. Posições e snapshots serão projeções/materializações, não substitutos do ledger.
4. DuckDB será usado para analytics quando volume e complexidade justificarem; Parquet armazenará séries históricas e dados normalizados volumosos.
5. Acesso ao armazenamento ficará atrás de repositórios; domínio não importa SQLite, Streamlit ou SDK de provedor.
6. Snapshots JSON existentes continuarão suportados durante a migração. Não gerar transações retroativas fictícias a partir de snapshots.

## Consequências positivas

- Operação simples e compatível com a VPS atual.
- Transações ACID e backup simples.
- Ledger auditável permite TWR/XIRR e reconstrução histórica.
- Evolução para DuckDB/Parquet sem trocar o domínio.

## Restrições e riscos

- SQLite suporta um escritor por vez; escritas devem ser curtas e concorrência controlada.
- WAL exige procedimento correto de backup.
- Migração de snapshots não recupera transações que nunca foram registradas.
- Importação e reconciliação precisam detectar duplicatas e transferências.

## Alternativas consideradas

- PostgreSQL: adiado; maior custo operacional sem benefício proporcional para uso individual.
- Event streaming/Kafka: descartado nesta escala.
- Somente snapshots: insuficiente para fluxo de caixa, retorno TWR/XIRR e auditoria.
