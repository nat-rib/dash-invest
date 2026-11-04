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

Gere um par de chaves SSH Ed25519 dedicado ao deploy. Adicione a chave pública ao arquivo `/home/deploy/.ssh/authorized_keys` da VPS e cadastre o conteúdo completo da chave privada no secret `VPS_SSH_PRIVATE_KEY`. Não versione a chave privada.

O workflow usa a action oficial `tailscale/github-action@v4`, autentica um runner efêmero com OAuth e conecta por SSH ao IP Tailscale da VPS (`100.104.34.5`). A VPS não precisa expor SSH publicamente.

## 2. Pré-requisitos na VPS

A VPS precisa estar com Docker Engine + Compose instalados, Tailscale conectado e o usuário `deploy` com sudo. O workflow faz o primeiro clone do repositório e executa o instalador automaticamente após o primeiro merge em `main`.

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
- Histórico SQLite: `/opt/personal-cloud/data/dash-invest/portfolio_history.db`
- Secrets Streamlit: `/opt/personal-cloud/data/dash-invest/.streamlit/secrets.toml`

O banco SQLite usa `HISTORY_DB_PATH=/app/data/portfolio_history.db`, portanto permanece no volume persistente mesmo com o filesystem do container em modo somente leitura.

O instalador cria uma carteira de exemplo somente se o arquivo ainda não existir. Importe seu JSON real pela página **Importação**. Não copie dados financeiros para o repositório.

Se for usar Alpha Vantage, copie `.streamlit/secrets.example.toml` para `/opt/personal-cloud/data/dash-invest/.streamlit/secrets.toml` e substitua o valor de exemplo pela sua chave. Nunca coloque a chave no Git.

## 5. Atualizações e diagnóstico

A partir daí, o deploy é automático ao integrar alterações em `main`. Para verificar:

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml ps
docker logs --tail=100 dash-invest
curl -fsS http://127.0.0.1:8501/_stcore/health
```
