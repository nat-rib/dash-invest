"""Adaptador CVM ITR (Informações Trimestrais).

Mesma estrutura de arquivos da DFP, mas cada conta do DRE pode aparecer em duas
janelas: o trimestre (até ~120 dias) e o acumulado do ano (YTD, mais de 120
dias). O trimestre mantém a métrica canônica (`revenue`) e o acumulado recebe o
sufixo `_ytd` (`revenue_ytd`), evitando misturar as duas séries no gráfico.

O provider é `cvm_itr` (distinto de `cvm`, usado pela DFP anual), então a mesma
métrica pode ser consultada por periodicidade sem colisão.
"""
from __future__ import annotations

import urllib.request
from dataclasses import dataclass

from src.domain.observations import Observation
from src.providers.base import FundamentalsBatch
from src.providers.cvm import (
    CVM_STATEMENTS,
    CvmArchive,
    parse_document_index,
    parse_issuers,
    parse_statement,
)

ITR_BASE_URL = "https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/ITR/DADOS"
ITR_PARSER_VERSION = "cvm-itr-v1"


def itr_url(year: int) -> str:
    if not 1999 <= year <= 2100:
        raise ValueError("ano da ITR fora do intervalo suportado")
    return f"{ITR_BASE_URL}/itr_cia_aberta_{year}.zip"


def download_itr(year: int, *, timeout: int = 240) -> bytes:
    request = urllib.request.Request(
        itr_url(year), headers={"User-Agent": "dash-invest/1.0 (+dados abertos CVM)"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


@dataclass(frozen=True)
class CvmItrProvider:
    """Provedor de fundamentos trimestrais da CVM; implementa `FundamentalsProvider`."""

    name: str = "cvm_itr"
    parser_version: str = ITR_PARSER_VERSION
    timeout: int = 240
    consolidated: bool = True

    def fetch(self, fiscal_year: int) -> FundamentalsBatch:
        archive = CvmArchive(download_itr(fiscal_year, timeout=self.timeout))
        names = set(archive.names())

        index_name = f"itr_cia_aberta_{fiscal_year}.csv"
        documents = (
            parse_document_index(archive.read_text(index_name)) if index_name in names else {}
        )

        suffix = "con" if self.consolidated else "ind"
        observations: list[Observation] = []
        for statement in CVM_STATEMENTS:
            member = f"itr_cia_aberta_{statement}_{suffix}_{fiscal_year}.csv"
            if member not in names:
                continue
            observations.extend(
                parse_statement(
                    archive.read_text(member),
                    statement=statement,
                    documents=documents,
                    consolidated=self.consolidated,
                    parser_version=self.parser_version,
                    provider=self.name,
                    metric_prefix="cvm_itr",
                    long_period_suffix="_ytd",
                )
            )

        return FundamentalsBatch(
            observations=observations,
            issuers=parse_issuers(documents, source="cvm"),
        )
