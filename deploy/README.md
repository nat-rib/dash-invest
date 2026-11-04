# Deploy na VPS (Docker + GHCR + Tailscale)

## Fluxo de CI/CD

- Push em `develop`: instala dependências e executa os testes. Não publica imagem nem faz deploy.
- Pull request com destino a `develop` ou `main`: executa os testes.
- Merge/push em `main`: executa os testes, publica `ghcr.io/nat-rib/dash-invest:latest` e faz deploy automático na VPS por SSH dentro da tailnet Tailscale.
- A carteira, o histórico SQLite e os secrets permanecem fora da imagem e do repositório.

## 1. Configurar os acessos do GitHub Actions

No painel de administração do Tailscale:

1. Crie a tag `tag:ci` e permita que o OAuth client a utilize.
2. Crie um OAuth client com permissão de escrita para criar auth keys/dispositivos e restrinja-o à tag `tag:ci`.
3. Nas regras de acesso (grants/ACL), permita que `tag:ci` acesse somente a VPS `srv2125797` na porta TCP 22. Não conceda acesso amplo à tailnet.

No GitHub, em **Settings → Secrets and variables → Actions → Secrets**, cadastre:

- `TS_OAUTH_CLIENT_ID`: ID do OAuth client do Tailscale.
- `TS_OAUTH_SECRET`: segredo do OAuth client.
- `VPS_SSH_PRIVATE_KEY`: chave privada SSH dedicada ao GitHub Actions (não reutilize a chave pessoal do Mac).

Gere um par de chaves dedicado localmente, por exemplo:

```bash
ssh-keygen -t ed25519 -C "github-actions-dash-invest" -f ./dash-invest-actions
```

Adicione o conteúdo de `dash-invest-actions.pub` ao final de `/home/deploy/.ssh/authorized_keys` na VPS. Cadastre o conteúdo completo de `dash-invest-actions` no secret `VPS_SSH_PRIVATE_KEY`. Guarde a chave privada com segurança e não a versione.

O workflow usa a action oficial `tailscale/github-action@v4`, autentica um runner efêmero com OAuth e conecta por SSH ao IP Tailscale da VPS (`100.104.34.5`). A VPS não precisa expor SSH publicamente.

## 2. Publicar a imagem GHCR

Depois do primeiro merge em `main`, o workflow cria o pacote `ghcr.io/nat-rib/dash-invest`. Se a VPS ainda não estiver autenticada no GHCR, deixe o pacote com visibilidade **Public** para permitir pull sem credenciais persistentes na VPS. A imagem contém apenas o código da aplicação, nunca dados da carteira.

## 3. Preparar a VPS (uma única vez)

Entre por SSH via Tailscale:

```bash
ssh deploy@100.104.34.5
```

Clone o repositório na branch principal e execute o instalador:

```bash
cd ~
git clone --branch main https://github.com/nat-rib/dash-invest.git
cd dash-invest
bash ./deploy/install.sh
```

O instalador cria os diretórios persistentes, inicializa a carteira com dados fictícios de exemplo se ainda não existir, ajusta as permissões para o usuário não-root do container e sobe a imagem.

O instalador adiciona `deploy` ao grupo GID 10001 para permitir administrar os arquivos persistentes. Encerre e abra novamente a sessão SSH para a nova associação de grupo valer.

Depois que o container estiver saudável, configure o acesso privado:

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

O banco SQLite agora usa `HISTORY_DB_PATH=/app/data/portfolio_history.db`, portanto permanece no volume persistente mesmo com o filesystem do container em modo somente leitura.

O instalador cria uma carteira de exemplo somente se o arquivo ainda não existir. Importe seu JSON real pela página **Importação**. Não copie dados financeiros para o repositório.

Se for usar Alpha Vantage, copie `.streamlit/secrets.example.toml` para `/opt/personal-cloud/data/dash-invest/.streamlit/secrets.toml` e substitua o valor de exemplo pela sua chave. Nunca coloque a chave no Git. Reinicie o container após alterar:

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml restart
```

## 5. Atualizações e diagnóstico

A partir daí, o deploy é automático ao integrar alterações em `main`. Para verificar:

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml ps
docker logs --tail=100 dash-invest
curl -fsS http://127.0.0.1:8501/_stcore/health
```

Se a VPS não conseguir baixar a imagem, confirme que o pacote GHCR está como Public e que a tag `latest` foi publicada pelo workflow.
