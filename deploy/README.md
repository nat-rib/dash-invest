# Deploy na VPS (Docker + GHCR + Tailscale)

## O que este deploy faz

- O GitHub Actions executa os testes e publica a imagem em `ghcr.io/nat-rib/dash-invest`.
- O container roda sem root (UID/GID 10001), com filesystem somente leitura e limite de 768 MB de RAM.
- Carteira, histórico SQLite e secrets ficam em `/opt/personal-cloud/data/dash-invest`, fora da imagem e do repositório.
- A porta do host é publicada somente em `127.0.0.1:8501`. Não abra a porta 8501 no firewall e não publique em `0.0.0.0`.

## 1. Publicar a imagem

Faça push na branch `develop`. O workflow `.github/workflows/docker-publish.yml` roda os testes e, se passarem, publica a imagem com a tag `develop`.

Na primeira publicação, abra as configurações do pacote no GitHub e altere a visibilidade para **Public**. Isso permite que a VPS faça pull sem armazenar um Personal Access Token nela. O código do dashboard já é público; a imagem contém somente o código da aplicação, nunca os dados pessoais.

## 2. Preparar a VPS

Entre por SSH via Tailscale:

```bash
ssh deploy@100.104.34.5
```

Clone o repositório e execute o instalador:

```bash
cd ~
git clone --branch develop https://github.com/nat-rib/dash-invest.git
cd dash-invest
bash ./deploy/install.sh
```

O instalador cria os diretórios persistentes, inicializa a carteira com dados fictícios de exemplo se ainda não existir, ajusta as permissões para o usuário não-root do container e sobe a imagem.

O instalador adiciona `deploy` ao grupo GID 10001 para permitir administrar os arquivos persistentes. Encerre e abra novamente a sessão SSH para a nova associação de grupo valer.

## 3. Configurar acesso privado pelo Tailscale

Na VPS, depois que o container estiver saudável:

```bash
sudo tailscale serve --bg http://127.0.0.1:8501
sudo tailscale serve status
```

Use a URL HTTPS `https://srv2125797.<seu-tailnet>.ts.net` mostrada pelo comando/status. O nome exato depende do tailnet. Isso usa Tailscale Serve, não Funnel: o serviço continua privado à tailnet.

Não configure Funnel, não crie regra pública para a porta 8501 e não altere o mapeamento `127.0.0.1:8501:8501`.

## 4. Atualizar depois de um push

O workflow publica a nova imagem automaticamente, mas o primeiro deploy é manual de propósito. Para atualizar a VPS:

```bash
cd ~/dash-invest
git pull --ff-only
bash ./deploy/install.sh
```

O script preserva a carteira, o banco SQLite e os secrets existentes.

## 5. Arquivos de dados e Alpha Vantage

- Carteira: `/opt/personal-cloud/data/dash-invest/portfolio.json`
- Histórico SQLite: `/opt/personal-cloud/data/dash-invest/portfolio_history.db`
- Secrets Streamlit: `/opt/personal-cloud/data/dash-invest/.streamlit/secrets.toml`

O instalador cria uma carteira de exemplo somente se o arquivo ainda não existir. Importe seu JSON real pela página **Importação**. Não copie dados financeiros para o repositório.

Se for usar Alpha Vantage, copie `.streamlit/secrets.example.toml` para `/opt/personal-cloud/data/dash-invest/.streamlit/secrets.toml` e substitua o valor de exemplo pela sua chave. Nunca coloque a chave no Git. Reinicie o container após alterar:

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml restart
```

## Diagnóstico

```bash
docker compose -f /opt/personal-cloud/apps/dash-invest/compose.yaml ps
docker logs --tail=100 dash-invest
curl -fsS http://127.0.0.1:8501/_stcore/health
```

Se a VPS não conseguir baixar a imagem, confirme que o pacote GHCR está como Public e que a tag `develop` foi publicada pelo workflow.
