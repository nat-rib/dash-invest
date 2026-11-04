# Dashboard pessoal de investimentos

Dashboard privado em Python/Streamlit para acompanhar uma carteira, operações e dados de mercado. A aplicação mantém o snapshot JSON legado e o ledger SQLite como fontes distintas até que exista uma reconciliação explícita entre eles.

## Instalação e uso

Requer Python 3.11 ou superior.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Ou, após a instalação inicial, execute `./run_dashboard.sh`.

O servidor foi configurado para ouvir somente em `127.0.0.1` e as estatísticas de uso do Streamlit ficam desativadas. Abra a URL exibida no terminal. A navegação é organizada em **Visão geral**, **Minha carteira**, **Investigar**, **Mercado** e **Configurações**. Use **Importar carteira** para validar e substituir o snapshot JSON por inteiro. Alternativamente, copie um JSON válido para `portfolio.json` na raiz do projeto.

Use `portfolio.example.json` como referência: todo o conteúdo é fictício. Nunca versione seu `portfolio.json` real.

## Interface e fontes de dados\n\nA Visão geral apresenta patrimônio e alocação conhecidos a partir do snapshot JSON configurado em `PORTFOLIO_PATH`. Ela informa essa origem explicitamente e não combina automaticamente o snapshot com o ledger SQLite. Rentabilidade TWR/XIRR permanece na seção **Minha carteira → Rentabilidade**, pois depende de fluxos e avaliações suficientes. Benchmark ainda não é calculado.\n\nA navegação é centralizada em `app.py`; estilos responsivos compartilhados ficam em `src/ui/theme.py`. A adaptação completa de tabelas e a validação em larguras/dispositivos reais seguem no roadmap da Fase 1.\n\n## Dados e cálculos

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

## Arquitetura e roadmap

A visão arquitetural, decisões técnicas e fases de implementação estão documentadas em [`docs/architecture/`](docs/architecture/README.md) e no [roadmap](docs/architecture/implementation-roadmap.md).
