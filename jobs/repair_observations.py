"""CLI: repara supersessão de observações duplicadas legadas.

Correções de parser podem deixar mais de uma versão ativa no mesmo slot sem que
tenha havido uma nova ingestão. O reparo mantém a versão mais recente.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.persistence.database import SQLiteDatabase
from src.persistence.observations import ObservationRepository


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Repara supersessão de observações.")
    parser.add_argument(
        "--db",
        type=Path,
        default=None,
        help="caminho do SQLite (padrão: DASH_INVEST_DB_PATH)",
    )
    args = parser.parse_args(argv)

    database_path = Path(
        args.db or os.environ.get("DASH_INVEST_DB_PATH", "data/dash_invest.db")
    ).resolve()
    # O container tem /tmp de 64 MB; temporários do SQLite vão para o volume.
    os.environ.setdefault("SQLITE_TMPDIR", str(database_path.parent))

    database = SQLiteDatabase(database_path)
    database.initialize()
    updated = ObservationRepository(database).repair_supersession()
    print(f"{updated} observações duplicadas marcadas como superseded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
