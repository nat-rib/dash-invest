"""Relatório de pesquisa baseado apenas em fatos calculados.

O agente não calcula indicadores nem inventa números: ele seleciona as
observações anuais da CVM, deriva razões determinísticas, cita a fonte de cada
afirmação e delega ao LLM apenas a redação. Sem LLM, a narrativa é montada de
forma determinística.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone

from src.ai.gateway import NarrativeGateway, ResearchError
from src.domain.issuers import Issuer
from src.domain.observations import Observation

RESEARCH_METRICS = ("revenue", "net_income", "equity", "total_assets")

SYSTEM_PROMPT = (
    "Você é um analista de investimentos. Use exclusivamente os fatos fornecidos. "
    "Nunca invente, estime ou arredonde números diferentes dos informados. "
    "Escreva em português, em no máximo três parágrafos, e mencione as limitações. "
    "Não faça recomendação de compra ou venda."
)


@dataclass(frozen=True)
class Claim:
    key: str
    text: str
    metric: str
    value: float
    unit: str
    reference_date: date | None
    source_url: str | None


@dataclass(frozen=True)
class ResearchReport:
    cnpj: str
    name: str
    generated_at: datetime
    narrative: str
    claims: tuple[Claim, ...]
    limitations: tuple[str, ...]
    sources: tuple[str, ...]
    gateway: str


def _brl(value: float) -> str:
    integer = f"{value:,.0f}"
    return "R$ " + integer.replace(",", "X").replace(".", ",").replace("X", ".")


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%".replace(".", ",")


def _dedupe_by_date(items: list[Observation]) -> list[Observation]:
    by_date: dict[date, Observation] = {}
    for item in items:
        by_date[item.reference_date] = item
    return [by_date[day] for day in sorted(by_date)]


def _group(observations: list[Observation]) -> dict[str, list[Observation]]:
    grouped: dict[str, list[Observation]] = {}
    for observation in observations:
        if observation.metric in RESEARCH_METRICS:
            grouped.setdefault(observation.metric, []).append(observation)
    return {metric: _dedupe_by_date(items) for metric, items in grouped.items()}


def _prompt(name: str, claims: list[Claim]) -> str:
    facts = [
        {
            "metrica": claim.metric,
            "texto": claim.text,
            "valor": claim.value,
            "unidade": claim.unit,
            "data": claim.reference_date.isoformat() if claim.reference_date else None,
            "fonte": claim.source_url,
        }
        for claim in claims
    ]
    return (
        f"Empresa: {name}.\n"
        f"Fatos verificados:\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        "Escreva uma análise objetiva usando somente esses fatos."
    )


def build_report(
    *,
    issuer: Issuer,
    observations: list[Observation],
    gateway: NarrativeGateway | None = None,
    generated_at: datetime | None = None,
) -> ResearchReport:
    grouped = _group(observations)
    latest = {metric: items[-1] for metric, items in grouped.items() if items}
    prior = {metric: items[-2] for metric, items in grouped.items() if len(items) >= 2}

    claims: list[Claim] = []

    def add_money(key: str, text: str, observation: Observation) -> None:
        claims.append(
            Claim(
                key=key,
                text=text,
                metric=observation.metric,
                value=float(observation.value),
                unit="BRL",
                reference_date=observation.reference_date,
                source_url=observation.source_document,
            )
        )

    for key, label in (
        ("revenue", "Receita"),
        ("net_income", "Lucro líquido"),
        ("equity", "Patrimônio líquido"),
        ("total_assets", "Ativo total"),
    ):
        observation = latest.get(key)
        if observation is not None:
            add_money(
                key,
                f"{label} de {_brl(float(observation.value))} em {observation.reference_date.year}",
                observation,
            )

    revenue = latest.get("revenue")
    net_income = latest.get("net_income")
    equity = latest.get("equity")
    assets = latest.get("total_assets")
    year = revenue.reference_date.year if revenue else (
        net_income.reference_date.year if net_income else None
    )

    margin = None
    if revenue and net_income and float(revenue.value) > 0:
        margin = float(net_income.value) / float(revenue.value)
        claims.append(
            Claim(
                key="net_margin",
                text=f"Margem líquida de {_pct(margin)} em {year}",
                metric="net_margin",
                value=margin,
                unit="ratio",
                reference_date=net_income.reference_date,
                source_url=net_income.source_document or revenue.source_document,
            )
        )

    roe = None
    if net_income and equity and float(equity.value) > 0:
        roe = float(net_income.value) / float(equity.value)
        claims.append(
            Claim(
                key="roe",
                text=f"ROE de {_pct(roe)} em {year}",
                metric="roe",
                value=roe,
                unit="ratio",
                reference_date=net_income.reference_date,
                source_url=net_income.source_document or equity.source_document,
            )
        )

    growth = None
    if revenue and "revenue" in prior and float(prior["revenue"].value) > 0:
        growth = float(revenue.value) / float(prior["revenue"].value) - 1
        prior_year = prior["revenue"].reference_date.year
        claims.append(
            Claim(
                key="revenue_growth",
                text=f"Receita variou {_pct(growth)} frente a {prior_year}",
                metric="revenue_growth",
                value=growth,
                unit="ratio",
                reference_date=revenue.reference_date,
                source_url=revenue.source_document,
            )
        )

    sentences: list[str] = []
    if revenue:
        sentences.append(f"a receita em {year} foi de {_brl(float(revenue.value))}")
    if net_income:
        sentences.append(f"o lucro líquido foi de {_brl(float(net_income.value))}")
    if margin is not None:
        sentences.append(f"a margem líquida ficou em {_pct(margin)}")
    if equity:
        sentences.append(f"o patrimônio líquido era de {_brl(float(equity.value))}")
    if roe is not None:
        sentences.append(f"o ROE foi de {_pct(roe)}")
    if growth is not None:
        sentences.append(
            f"a receita variou {_pct(growth)} frente a {prior['revenue'].reference_date.year}"
        )

    if sentences:
        narrative = (
            f"{issuer.name} " + "; ".join(sentences) +
            ". Os números vêm das demonstrações financeiras padronizadas publicadas na CVM."
        )
    else:
        narrative = f"Não há observações anuais suficientes para analisar {issuer.name}."

    limitations: list[str] = [
        "Baseado apenas em demonstrações anuais (DFP) da CVM; preço, múltiplos e eventos recentes não são considerados.",
        "Reapresentações podem alterar números; consulte o documento oficial.",
        "Não é recomendação de investimento.",
        "Busca textual/FTS5 ainda não habilitada; as fontes são links oficiais.",
    ]
    if not prior:
        limitations.append("Sem exercício anterior para comparar crescimento.")

    gateway_name = "deterministic"
    if gateway is None:
        limitations.append("Nenhum gateway de IA configurado; narrativa determinística.")
    else:
        try:
            narrative = gateway.summarize(
                system=SYSTEM_PROMPT, prompt=_prompt(issuer.name, claims)
            )
            gateway_name = gateway.name
        except ResearchError:
            limitations.append("Gateway de IA indisponível; narrativa determinística usada.")

    sources = tuple(
        sorted({claim.source_url for claim in claims if claim.source_url})
    )

    return ResearchReport(
        cnpj=issuer.cnpj,
        name=issuer.name,
        generated_at=generated_at or datetime.now(timezone.utc),
        narrative=narrative,
        claims=tuple(claims),
        limitations=tuple(limitations),
        sources=sources,
        gateway=gateway_name,
    )
