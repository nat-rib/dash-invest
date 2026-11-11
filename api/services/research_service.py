"""Serviço de pesquisa: emissores e observações anuais da CVM."""
from __future__ import annotations

from typing import Any

from src.ai.gateway import NarrativeGateway
from src.ai.research import ResearchReport, build_report


def build(
    repositories: Any,
    cnpj: str,
    *,
    gateway: NarrativeGateway | None = None,
) -> ResearchReport:
    issuer = repositories.issuers.get(cnpj)
    if issuer is None:
        raise LookupError("Emissor não encontrado.")
    observations = repositories.observations.list(
        provider="cvm", instrument_id=f"cnpj:{issuer.cnpj}"
    )
    return build_report(issuer=issuer, observations=observations, gateway=gateway)
