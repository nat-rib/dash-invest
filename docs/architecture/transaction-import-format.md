# Contrato de importação de transações CSV

O importador inicial recebe um CSV canônico independente de corretora. Extratos de bancos e corretoras devem ser convertidos para este contrato por adaptadores específicos; o arquivo original nunca é tratado como se tivesse um layout universal.

## Colunas

Obrigatórias:

- `external_id`: identificador estável da operação na instituição. É a chave de idempotência.
- `occurred_at`: timestamp ISO-8601 com timezone, por exemplo `2026-11-04T10:30:00-03:00`.
- `transaction_type`: valor de `TransactionType` (BUY, SELL, DEPOSIT, WITHDRAWAL, DIVIDEND, JCP, INTEREST, COUPON, AMORTIZATION, TAX, FEE, SPLIT, BONUS, TRANSFER_IN ou TRANSFER_OUT).
- `institution`: instituição/corretora que reportou a operação.
- `currency`: código ISO 4217 de três letras.

Opcionais: `instrument_id`, `quantity`, `unit_price`, `amount`, `fees`, `taxes`, `sequence`, `transfer_id`, `notes` e `metadata_json`.

Valores decimais usam ponto como separador decimal. Datas sem timezone são rejeitadas. `metadata_json` deve ser um objeto JSON. Operações BUY/SELL precisam de instrumento, quantidade e preço unitário; demais regras são validadas pelo modelo de domínio.

## Garantias

- O arquivo inteiro é validado antes da persistência.
- O lote é gravado em uma única transação SQLite: um erro não deixa importação parcial.
- Reimportar a mesma operação com o mesmo `portfolio_id`, `institution` e `external_id` não duplica o ledger.
- Reutilizar a mesma chave externa com conteúdo diferente é erro, não sobrescrita.
- Identificadores internos são determinísticos para o mesmo escopo/chave externa.
- O ledger continua append-only.

## Transferências

Eventos TRANSFER_IN/TRANSFER_OUT podem ser importados inicialmente sem `transfer_id`. O serviço de reconciliação sugere pares com mesma carteira, instituição distinta, moeda, instrumento, quantidade e valor compatíveis, dentro de uma janela de datas configurável.

Somente relações um-para-um são sugeridas como não ambíguas. Múltiplas correspondências, transferências incompletas e pares explícitos inconsistentes são reportados separadamente. O serviço não modifica nem confirma eventos automaticamente: uma futura UI deve permitir revisão antes de associar as pontas.

Para transferência de ativo, `amount` representa custo contábil transferido, não valor de mercado. Para transferência de caixa, representa o valor monetário movimentado.
