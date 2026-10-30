#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON" ]]; then
  echo "Ambiente virtual não encontrado em .venv. Execute primeiro:"
  echo "python3.11 -m venv .venv && .venv/bin/python -m pip install -r requirements.txt"
  exit 1
fi

exec "$PYTHON" -m streamlit run "$PROJECT_DIR/app.py" --server.address 127.0.0.1
