# Migração do snapshot legado e performance da carteira

## Migração JSON → SQLite

A página **Ledger e operações → Migrar carteira JSON** lê o arquivo indicado por `PORTFOLIO_PATH` (padrão `portfolio.json`) e chama `PortfolioSnapshotImporter`.

- A migração cria/atualiza a carteira `legacy-import`, o catálogo de instrumentos e snapshots de posição.
- O arquivo JSON não é apagado, renomeado ou sobrescrito.
- Nenhuma transação é inventada a partir de uma posição agregada.
- A operação é transacional e pode ser repetida. Importações do mesmo snapshot/data-base atualizam a projeção correspondente.
- O banco do ledger usa `DASH_INVEST_DB_PATH`; em produção deve apontar para o volume persistente, fora da imagem.

O dashboard legado continua lendo o JSON até uma migração futura da experiência principal. A tela nova não troca a fonte do dashboard silenciosamente.

## Importação de extratos

A página **Ledger e operações → Importar extrato CSV** permite mapear colunas de um CSV de banco/corretora para o modelo universal. É necessário indicar instituição, moeda padrão, formato decimal, formato de data e timezone para datas sem offset.

Tipos comuns em português são normalizados (compra, venda, aporte, retirada, dividendo, JCP, juros, cupom, amortização, taxa, imposto, bonificação, desdobramento e transferência). O código do ativo precisa ser associado a um instrumento do catálogo. Isso evita gravar tickers como IDs internos.

Quando o extrato não contém ID estável, o adaptador cria um fingerprint SHA-256 do conteúdo da linha, com ordinal para linhas idênticas. Esse fallback é determinístico ao reimportar o mesmo arquivo sem reordená-lo; um identificador nativo da instituição é preferível.

A importação inteira é validada antes da gravação e usa uma transação SQLite. Uma linha inválida rejeita o lote completo. Colisões de ID externo com conteúdo diferente nunca sobrescrevem o ledger.

## Conciliação de transferências

A tela **Conciliar transferências** exibe apenas sugestões de correspondência única. A confirmação humana grava um vínculo em `transfer_links`, sem atualizar ou apagar as transações originais. As duas pontas precisam pertencer à mesma carteira, ser TRANSFER_OUT/TRANSFER_IN, ter instituições distintas e compartilhar moeda/instrumento. Diferenças de valor/quantidade podem ser aceitas somente por decisão explícita do usuário.

Transferências entre moedas distintas não são pareadas automaticamente: precisam de tratamento cambial específico.

## Rentabilidade

### TWR

O motor recebe períodos contíguos com valor inicial e valor final observado imediatamente após o fluxo externo no limite do período. Aporte é positivo no ponto de vista da carteira; retirada é negativa. Para cada subperíodo:

`r_i = (V_{fim, após fluxo} - F_i) / V_{início} - 1`

O retorno acumulado é o produto dos fatores `(1 + r_i)`, menos um. Não inserir fluxo externo como provento. Avaliações devem estar na mesma moeda e nos limites corretos dos fluxos.

### XIRR

Os fluxos usam a ótica do investidor: aporte negativo, retirada positiva e patrimônio terminal positivo na data de avaliação. As datas reais determinam a fração anual por base de 365 dias. Transferências internas, dividendos e juros não entram como aporte/retirada externa; o valor terminal deve incluir o patrimônio/cash da carteira conforme a avaliação escolhida.

O cálculo rejeita mistura de moedas sem FX, datas insuficientes e casos em que a busca detecta múltiplas raízes. XIRR é retorno ponderado pelo dinheiro e não deve ser confundido com TWR.

## Produção

O SQLite do ledger deve usar `/app/data/dash_invest.db`, montado em volume persistente. Antes do primeiro deploy, confirmar backup do diretório de dados, permissões de escrita do UID/GID 10001, secrets GitHub e conectividade Tailscale/SSH. A porta 8501 permanece vinculada a loopback na VPS; o acesso externo é exclusivamente Tailscale Serve.
