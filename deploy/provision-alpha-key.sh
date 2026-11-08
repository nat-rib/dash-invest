#!/usr/bin/env bash
# Provisiona a chave do Alpha Vantage na VPS.
#
# Roda no seu Mac, na raiz do repositório:
#   bash deploy/provision-alpha-key.sh
#
# Lê a chave de .streamlit/secrets.toml (ou pede via read -s) e envia para
# /opt/personal-cloud/apps/dash-invest/.env, com modo 600. A chave nunca é
# impressa na tela nem fica no histórico do shell.
set -Eeuo pipefail

VPS_HOST="${VPS_HOST:-deploy@100.104.34.5}"
APP_DIR="${APP_DIR:-/opt/personal-cloud/apps/dash-invest}"
LOCAL_SECRETS="${LOCAL_SECRETS:-.streamlit/secrets.toml}"
PUSH=0
[[ "${1:-}" == "--push" ]] && PUSH=1

die() { echo "erro: $*" >&2; exit 1; }

[[ -f deploy/compose.yaml ]] || die "rode na raiz do repositório (deploy/compose.yaml não encontrado)"
grep -q 'ALPHA_VANTAGE_API_KEY' deploy/compose.yaml \
  || die "deploy/compose.yaml não injeta ALPHA_VANTAGE_API_KEY; atualize o repositório"

if [[ -f "$LOCAL_SECRETS" ]]; then
  KEY=$(sed -n 's/^[[:space:]]*ALPHA_VANTAGE_API_KEY[[:space:]]*=[[:space:]]*"\(.*\)"/\1/p' "$LOCAL_SECRETS" | head -n1)
else
  read -rsp "ALPHA_VANTAGE_API_KEY: " KEY
  echo
fi
[[ -n "${KEY:-}" ]] || die "chave vazia ou não encontrada (esperado em $LOCAL_SECRETS)"

echo "==> enviando compose.yaml para $VPS_HOST"
scp -q deploy/compose.yaml "$VPS_HOST:/tmp/dash-invest-compose.yaml"
ssh "$VPS_HOST" "install -m 640 /tmp/dash-invest-compose.yaml '$APP_DIR/compose.yaml'"

echo "==> gravando .env na VPS (modo 600)"
printf 'ALPHA_VANTAGE_API_KEY=%s\n' "$KEY" |
  ssh "$VPS_HOST" "umask 077; cat > '$APP_DIR/.env' && chmod 600 '$APP_DIR/.env'"

echo "==> recriando o container"
ssh "$VPS_HOST" "cd '$APP_DIR' && docker compose up -d --force-recreate"

echo "==> verificando"
ssh "$VPS_HOST" \
  "docker exec dash-invest sh -lc 'test -n \"\$ALPHA_VANTAGE_API_KEY\" && echo configurada'"

echo
echo "Pronto. Recarregue a página Mercado."

# Opcional: deixa a correção permanente no repositório. O deploy sobrescreve
# o compose.yaml da VPS, então sem isso a linha some no próximo push em main.
if [[ "$PUSH" == 1 ]]; then
  [[ "$(git branch --show-current)" == "main" ]] || die "para --push, esteja na branch main"
  echo
  echo "==> commitando e publicando em main"
  git add deploy/compose.yaml deploy/install.sh deploy/README.md \
          deploy/provision-alpha-key.sh .github/workflows/docker-publish.yml \
          README.md .env.example .streamlit/secrets.example.toml
  if git diff --cached --quiet; then
    echo "nada novo para commitar"
  else
    git commit -m "chore(deploy): injeta ALPHA_VANTAGE_API_KEY via .env do compose"
    git push origin main
  fi
fi
