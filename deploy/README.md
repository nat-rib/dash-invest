# Deploy na VPS (Docker + GHCR + Tailscale)

## Fluxo de CI/CD

- Push em `develop`: instala dependências e executa os testes. Não publica imagem nem faz deploy.
- Pull request com destino a `develop` ou `main`: executa os testes.
- Merge/push em `main`: executa os testes, publica `ghcr.io/nat-rib/dash-invest:latest` e faz deploy automático na VPS por SSH dentro da tailnet Tailscale.
- O workflow autentica temporariamente a VPS no GHCR com o `GITHUB_TOKEN` do job e faz logout ao terminar. O pacote pode permanecer privado.
- No primeiro deploy, o workflow clona a branch `main` na VPS e executa `deploy/install.sh`. Nos deploys seguintes, apenas faz pull e recria o container.
- A carteira, o histórico SQLite e os secrets permanecem fora da imagem e do repositório.

## 1. Configurar os acessos do GitHub Actions

No painel de administração do Tailscale:

1. Crie a tag `tag:ci` e permita que o OAuth client a utilize.
2. Crie um OAuth client com permissão para criar auth keys/dispositivos e restrinja-o à tag `tag:ci`.
3. Nas regras de acesso (grants/ACL), permita que `tag:ci` acesse somente a VPS `100.104.34.5` na porta TCP 22. Não conceda acesso amplo à tailnet.

No GitHub, em **Settings → Secrets and variables → Actions → Secrets**, cadastre:

- `TS_OAUTH_CLIENT_ID`: ID do OAuth client do Tailscale.
- `TS_OAUTH_SECRET`: segredo do OAuth client.
- `VPS_SSH_PRIVATE_KEY`: chave privada SSH dedicada ao GitHub Actions (não reutilize a chave pessoal do Mac).
- `ALPHA_VANTAGE_API_KEY` (opcional): chave de mercado provisionada no `.env` da VPS durante o deploy; veja a seção 5.

Gere um par de chaves SSH Ed25519 dedicado ao deploy. Adicione a chave pública ao arquivo `/home/deploy/.ssh/authorized_keys` da VPS e cadastre o conteúdo completo da chave privada no secret `VPS_SSH_PRIVATE_KEY`. Não versione a chave privada.

Ao rotacionar a chave, atualize os dois lados na mesma janela: adicione a pública nova em `authorized_keys`, remova a antiga e atualize o secret `VPS_SSH_PRIVATE_KEY` com a privada nova. O workflow valida a chave no step **Configure SSH** e imprime apenas o fingerprint; se o secret ficar defasado, o preflight falha com mensagem explícita em vez de erro genérico.

O workflow usa a action oficial `tailscale/github-action@v4`, autentica um runner efêmero com OAuth e conecta por SSH ao IP Tailscale da VPS (`100.104.34.5`). A VPS não precisa expor SSH publicamente.

## 2. Pré-requisitos na VPS

A VPS precisa estar com Docker Engine + Compose instalados, Tailscale conectado e o usuário `deploy` com acesso ao Docker sem sudo (por exemplo, grupo `docker`). O primeiro deploy também exige `sudo -n true` e permissões administrativas sem senha para o instalador preparar o grupo/UID/GID 10001 e os diretórios persistentes. O workflow faz um preflight SSH/Docker/sudo antes de clonar ou alterar o serviço.

O workflow usa o `GITHUB_TOKEN` com permissão de leitura para autenticar temporariamente no GHCR durante cada deploy e faz logout ao terminar. Não é necessário tornar o pacote público nem guardar um PAT permanente no servidor.

## 3. Configurar acesso privado ao app

Depois do primeiro deploy, conecte à VPS e configure o Tailscale Serve uma única vez:

```bash
sudo tailscale serve --bg http://127.0.0.1:8501
sudo tailscale serve status
```

Use a URL HTTPS `https://srv2125797.<seu-tailnet>.ts.net` mostrada pelo comando/status. Isso usa Tailscale Serve, não Funnel: o serviço continua privado à tailnet.

Não configure Funnel, não crie regra pública para a porta 8501 e não altere o mapeamento `127.0.0.1:8501:8501`.

## 4. Dados persistentes

- Carteira: `/opt/personal-cloud/data/dash-invest/portfolio.json`
- Histórico legado: `/opt/personal-cloud/data/dash-invest/portfolio_history.db`
- Ledger SQLite: `/opt/personal-cloud/data/dash-invest/dash_invest.db`
- Segredos de runtime: `/opt/personal-cloud/apps/dash-invest/.env` (fora do Git e da imagem)

O banco SQLite usa `HISTORY_DB_PATH=/app/data/portfolio_history.db`, portanto permanece no volume persistente mesmo com o filesystem do container em modo somente leitura.

O instalador cria uma carteira de exemplo somente se o arquivo ainda não existir. Importe seu JSON real pela página **Importação**. Não copie dados financeiros para o repositório.

## 5. Segredos de runtime (Alpha Vantage)

O container de produção roda **FastAPI**, que lê a chave de `ALPHA_VANTAGE_API_KEY` no ambiente do processo — não de `secrets.toml`. O `.env` fica ao lado do `compose.yaml` e é lido pelo Docker Compose; ele **não** é sobrescrito pelos deploys, ao contrário do `compose.yaml`.

Crie o arquivo uma única vez na VPS:

```bash
cd /opt/personal-cloud/apps/dash-invest
umask 077
printf 'ALPHA_VANTAGE_API_KEY=%s\n' 'SUA_CHAVE' > .env
chown deploy:deploy .env
chmod 600 .env
docker compose up -d --force-recreate
```

Confira sem imprimir a chave:

```bash
docker exec dash-invest sh -lc 'test -n "$ALPHA_VANTAGE_API_KEY" && echo configurada'
```

Alternativa gerenciada pelo GitHub: cadastre o secret `ALPHA_VANTAGE_API_KEY` em **Settings → Secrets and variables → Actions**. O job de deploy grava esse valor em `/opt/personal-cloud/apps/dash-invest/.env` (modo `600`) antes de recriar o container. Se o secret não existir, o `.env` manual é preservado. Atenção: quando o secret existe, ele passa a ser a fonte da verdade e sobrescreve esse arquivo a cada deploy.

Nunca passe a chave como `ARG`/`ENV` no `Dockerfile` nem a versione: ela ficaria gravada na imagem publicada no GHCR. Se a chave vazar, gere outra no Alpha Vantage.

## 6. Atualizações e diagnóstico

Antes de atualizar, a esteira pausa o container para criar um backup consistente do diretório de dados em `/opt/personal-cloud/data/dash-invest-backups`, mantendo os sete backups mais recentes. Depois do deploy, aguarda o healthcheck; se a imagem nova não ficar saudável, tenta voltar à imagem anterior. O rollback automático cobre a imagem/container, não substitui o procedimento de restauração manual de dados.

A partir daí, o deploy é automático ao integrar alterações em `main`. Para verificar:

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml ps
docker logs --tail=100 dash-invest
curl -fsS http://127.0.0.1:8501/api/health
```

## 7. Atualização diária de cotações

O timer systemd `dash-invest-prices.timer` executa todos os dias às **06:15** (America/Sao_Paulo) o job `jobs.ingest_prices_daily` dentro do container. Ele lê os tickers de `portfolio.json`, consulta o Alpha Vantage e grava as observações de fechamento (`metric=close`). O job é idempotente, ignora cripto e processa até 20 símbolos por execução (cota gratuita de ~25 req/dia). Símbolos excedentes ficam registrados no log.

O `install.sh` instala e habilita o timer no primeiro deploy. Em uma VPS já existente, instale manualmente:

```bash
cd /home/deploy/dash-invest
sudo install -m 644 deploy/systemd/dash-invest-prices.service /etc/systemd/system/
sudo install -m 644 deploy/systemd/dash-invest-prices.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now dash-invest-prices.timer
```

Verificar e testar:

```bash
systemctl list-timers dash-invest-prices.timer
journalctl -u dash-invest-prices.service -n 50 --no-pager
sudo systemctl start dash-invest-prices.service   # executa agora
```

O timer usa o timezone do host (`timedatectl`). Se o host não estiver em `America/Sao_Paulo`, ajuste o `OnCalendar` ou o timezone da VPS.
