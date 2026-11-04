#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/personal-cloud/apps/dash-invest"
DATA_DIR="/opt/personal-cloud/data/dash-invest"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine e Docker Compose precisam estar instalados."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "O usuário deploy precisa acessar o Docker sem sudo (grupo docker ou socket equivalente)."
  exit 1
fi

if ! sudo -n true 2>/dev/null; then
  echo "O primeiro deploy exige sudo sem senha para o usuário deploy (groupadd/usermod/chown/chmod)."
  echo "Faça o bootstrap administrativo manual e execute novamente."
  exit 1
fi

# O container usa UID/GID 10001. Prepare os diretórios com privilégios
# antes de tentar gravar neles: o usuário deploy pode ainda não ser owner.
if ! getent group 10001 >/dev/null; then
  sudo -n groupadd --system --gid 10001 dash-invest
fi
APP_GROUP="$(getent group 10001 | cut -d: -f1)"
sudo -n usermod -aG "$APP_GROUP" deploy
sudo -n install -d -m 755 -o deploy -g deploy "$APP_DIR"
sudo -n install -d -m 2770 -o 10001 -g "$APP_GROUP" "$DATA_DIR" "$DATA_DIR/.streamlit"

if [[ ! -f "$DATA_DIR/portfolio.json" ]]; then
  sudo -n install -m 660 -o 10001 -g "$APP_GROUP" \
    "$REPO_DIR/portfolio.example.json" "$DATA_DIR/portfolio.json"
  echo "Criado portfolio.json inicial com dados fictícios."
fi

if [[ ! -f "$DATA_DIR/.streamlit/secrets.toml" ]]; then
  sudo -n install -m 640 -o 10001 -g "$APP_GROUP" /dev/null "$DATA_DIR/.streamlit/secrets.toml"
fi

sudo -n chown -R "10001:$APP_GROUP" "$DATA_DIR"
sudo -n find "$DATA_DIR" -type d -exec chmod 2770 {} +
sudo -n find "$DATA_DIR" -type f -exec chmod 660 {} +
sudo -n chmod 640 "$DATA_DIR/.streamlit/secrets.toml"

install -m 640 "$REPO_DIR/deploy/compose.yaml" "$APP_DIR/compose.yaml"

cd "$APP_DIR"
docker compose pull
docker compose up -d --remove-orphans

echo
echo "Deploy concluído. Verifique com:"
echo "  docker compose -f $APP_DIR/compose.yaml ps"
echo "  docker logs -f dash-invest"
echo
echo "A aplicação está publicada somente em 127.0.0.1:8501."
echo "Configure o Tailscale Serve separadamente para acessá-la pela tailnet."
