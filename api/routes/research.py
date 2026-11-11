"""Rotas da pesquisa assistida por IA (Fase 7)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from api.dependencies import Repositories as RepositoryBundle
from api.dependencies import get_repositories
from api.schemas.research import ClaimOut, ResearchReportOut
from api.services import research_service
from src.ai.gateway import gateway_from_env

router = APIRouter(prefix="/api", tags=["research"])

Repositories = Annotated[RepositoryBundle, Depends(get_repositories)]


@router.get("/research/{cnpj:path}", response_model=ResearchReportOut)
def research(repositories: Repositories, cnpj: str) -> ResearchReportOut:
    try:
        report = research_service.build(
            repositories, cnpj, gateway=gateway_from_env()
        )
    except LookupError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return ResearchReportOut(
        cnpj=report.cnpj,
        name=report.name,
        generated_at=report.generated_at,
        narrative=report.narrative,
        claims=[
            ClaimOut(
                key=claim.key,
                text=claim.text,
                metric=claim.metric,
                value=claim.value,
                unit=claim.unit,
                reference_date=claim.reference_date,
                source_url=claim.source_url,
            )
            for claim in report.claims
        ],
        limitations=list(report.limitations),
        sources=list(report.sources),
        gateway=report.gateway,
    )
