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

O servidor foi configurado para ouvir somente em `127.0.0.1` e as estatísticas de uso do Streamlit ficam desativadas. Abra a URL exibida no terminal e use **Importação** para validar e substituir a carteira por inteiro. Alternativamente, copie um JSON válido para `portfolio.json` na raiz do projeto.

Use `portfolio.example.json` como referência: todo o conteúdo é fictício. Nunca versione seu `portfolio.json` real.

## Dados e cálculos

- Classes aceitas: `acao`, `fii`, `renda_fixa`, `etf`, `exterior`, `cripto`, `fundo`, `outros`, `caixa` e `credito_privado_coletivo`.
- O valor vem de `current_value`, quando informado; caso contrário, de `quantity × current_price`.
- Patrimônio consolidado soma somente valores conhecidos em BRL. Moedas estrangeiras ficam separadas — não ocorre conversão implícita.
- Ganho e rentabilidade só aparecem quando custo e valor atual são calculáveis e comparáveis.
- Um snapshot não fornece histórico: não são calculados TWR, XIRR, proventos ou retorno acumulado.

## Privacidade

Os dados ficam somente nos arquivos locais usados pela aplicação e não são enviados a serviços externos por este projeto. Isso não significa que estejam criptografados: a proteção em repouso depende do FileVault do macOS ou de um volume criptografado configurado por você. Não coloque senhas, tokens ou credenciais no JSON.

## Testes

```bash
pytest
```
