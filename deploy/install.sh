#!/usr/bin/env bash
set -Eeuo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="/opt/personal-cloud/apps/dash-invest"
DATA_DIR="/opt/personal-cloud/data/dash-invest"

if ! command -v docker >/dev/null 2>&1 || ! docker compose version >/dev/null 2>&1; then
  echo "Docker Engine e Docker Compose precisam estar instalados."
  exit 1
fi

mkdir -p "$APP_DIR" "$DATA_DIR/data" "$DATA_DIR/.streamlit"
chmod 700 "$DATA_DIR" "$DATA_DIR/data" "$DATA_DIR/.streamlit"

if [[ ! -f "$DATA_DIR/portfolio.json" ]]; then
  cp "$REPO_DIR/portfolio.example.json" "$DATA_DIR/portfolio.json"
  echo "Criado portfolio.json inicial com dados fictícios."
fi

if [[ ! -f "$DATA_DIR/.streamlit/secrets.toml" ]]; then
  : > "$DATA_DIR/.streamlit/secrets.toml"
  chmod 600 "$DATA_DIR/.streamlit/secrets.toml"
fi

# O processo dentro do container roda como UID/GID 10001.
sudo chown -R 10001:10001 "$DATA_DIR"
sudo chmod 600 "$DATA_DIR/portfolio.json" "$DATA_DIR/.streamlit/secrets.toml"
sudo chmod 700 "$DATA_DIR" "$DATA_DIR/data" "$DATA_DIR/.streamlit"

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
echo "Depois configure o Tailscale Serve para acessá-la pela tailnet."
