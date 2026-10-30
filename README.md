# Dashboard pessoal de investimentos

Dashboard local em Python/Streamlit para visualizar um snapshot de carteira fornecido em JSON. Não há integrações com corretoras, contas, APIs externas ou internet.

## Instalação e uso

Requer Python 3.11 ou superior.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Ou, após a instalação inicial, execute `./run_dashboard.sh`.

O servidor foi configurado para ouvir somente em `127.0.0.1` e as estatísticas de uso do Streamlit ficam desativadas. Abra a URL exibida no terminal e use **Importação** para validar e substituir a carteira por inteiro. Alternativamente, copie um JSON válido para `portfolio.json` na raiz do projeto.

Use `portfolio.example.json` como referência: todo o conteúdo é fictício. Nunca versione seu `portfolio.json` real.

## Dados e cálculos

- Classes aceitas: `acao`, `fii`, `renda_fixa`, `etf`, `exterior`, `cripto`, `fundo`, `outros`, `caixa` e `credito_privado_coletivo`.
- O valor vem de `current_value`, quando informado; caso contrário, de `quantity × current_price`.
- Patrimônio consolidado soma valores conhecidos em BRL e valores estrangeiros somente quando houver taxa e valor de conversão para BRL registrados explicitamente. Não ocorre conversão implícita.
- Ganho e rentabilidade só aparecem quando custo e valor atual são calculáveis e comparáveis.
- Um snapshot não fornece histórico: não são calculados TWR, XIRR, proventos ou retorno acumulado.

## Privacidade

Os dados ficam somente nos arquivos locais usados pela aplicação e não são enviados a serviços externos por este projeto. Isso não significa que estejam criptografados: a proteção em repouso depende do FileVault do macOS ou de um volume criptografado configurado por você. Não coloque senhas, tokens ou credenciais no JSON.

## Dados de mercado opcionais

A página **Mercado** pode consultar cotações e histórico diário no Alpha Vantage. Crie `.streamlit/secrets.toml` a partir de `.streamlit/secrets.example.toml` e inclua sua chave; nunca versione esse arquivo. A consulta envia somente o símbolo do ativo ao Alpha Vantage — não envia saldos, quantidades ou instituições. Por padrão, ações, FIIs e ETFs em BRL usam o sufixo `.SAO`; se necessário, defina `market_symbol` na posição do JSON. A atualização de preços sempre mostra uma prévia e requer confirmação antes de substituir o snapshot.

## Histórico local

Cada consulta bem-sucedida na página **Mercado** registra um snapshot em `data/portfolio_history.db`, um banco SQLite local ignorado pelo Git. A página **Histórico** mostra a evolução dos valores e das posições. Ela não calcula retorno TWR, XIRR ou rentabilidade total: para isso também é necessário registrar cada aporte, retirada, imposto e provento.

## Testes

```bash
pytest
```
