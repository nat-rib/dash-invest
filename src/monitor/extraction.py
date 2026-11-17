"""Extração determinística de ativos em textos de notícias.

Cobre tickers (ações, FIIs, ETFs), CNPJ de emissores, criptoativos e produtos
de renda fixa (Tesouro, CDB, LCI/LCA, CRI/CRA, debêntures). A confiança é
explícita: ticker exato > nome de companhia > sufixo inferido.
"""
from __future__ import annotations

import re
import unicodedata
from collections.abc import Mapping

from src.domain.signals import AssetMention

TICKER_RE = re.compile(r"\b([A-Z]{4}\d{1,2})\b")
CNPJ_RE = re.compile(r"\b\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}\b")
CRYPTO_SYMBOLS = (
    "BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "USDT",
    "USDC", "AVAX", "DOT", "LINK", "LTC", "BCH",
)

# ticker -> (nome, classe)
TICKERS: dict[str, tuple[str, str]] = {
    # ações
    "PETR4": ("Petrobras PN", "acao"), "PETR3": ("Petrobras ON", "acao"),
    "VALE3": ("Vale ON", "acao"), "ITUB4": ("Itaú Unibanco PN", "acao"),
    "ITUB3": ("Itaú Unibanco ON", "acao"), "BBDC4": ("Bradesco PN", "acao"),
    "BBDC3": ("Bradesco ON", "acao"), "BBAS3": ("Banco do Brasil ON", "acao"),
    "ABEV3": ("Ambev ON", "acao"), "WEGE3": ("WEG ON", "acao"),
    "MGLU3": ("Magazine Luiza ON", "acao"), "B3SA3": ("B3 ON", "acao"),
    "SUZB3": ("Suzano ON", "acao"), "ELET3": ("Eletrobras ON", "acao"),
    "ELET6": ("Eletrobras PNB", "acao"), "GGBR4": ("Gerdau PN", "acao"),
    "CSNA3": ("CSN ON", "acao"), "RENT3": ("Localiza ON", "acao"),
    "RADL3": ("Raia Drogasil ON", "acao"), "LREN3": ("Lojas Renner ON", "acao"),
    "VIVT3": ("Telefônica Brasil ON", "acao"), "TOTS3": ("Totvs ON", "acao"),
    "HAPV3": ("Hapvida ON", "acao"), "RAIL3": ("Rumo ON", "acao"),
    "CMIG4": ("Cemig PN", "acao"), "SANB11": ("Santander Brasil Unit", "acao"),
    "BPAC11": ("BTG Pactual Unit", "acao"), "NTCO3": ("Natura ON", "acao"),
    "AZUL4": ("Azul PN", "acao"), "GOLL4": ("Gol PN", "acao"),
    "CVCB3": ("CVC Brasil ON", "acao"), "CYRE3": ("Cyrela ON", "acao"),
    "BRFS3": ("BRF ON", "acao"), "MRFG3": ("Marfrig ON", "acao"),
    "JBSS3": ("JBS ON", "acao"), "PRIO3": ("PRIO ON", "acao"),
    "RRRP3": ("3R Petroleum ON", "acao"), "CPLE6": ("Copel PNB", "acao"),
    "EQTL3": ("Equatorial ON", "acao"), "ENGI11": ("Engie Brasil Unit", "acao"),
    "SBSP3": ("Sabesp ON", "acao"), "KLBN11": ("Klabin Unit", "acao"),
    "EMBR3": ("Embraer ON", "acao"), "CSAN3": ("Cosan ON", "acao"),
    "UGPA3": ("Ultrapar ON", "acao"), "BRKM5": ("Braskem PNA", "acao"),
    "USIM5": ("Usiminas PNA", "acao"), "TUPY3": ("Tupy ON", "acao"),
    # FIIs
    "HGLG11": ("CSHG Logística", "fii"), "KNRI11": ("Kinea Renda Imobiliária", "fii"),
    "MXRF11": ("Maxi Renda", "fii"), "XPLG11": ("XP Log", "fii"),
    "VISC11": ("Vinci Shopping Centers", "fii"), "BTLG11": ("BTG Logística", "fii"),
    "KNCR11": ("Kinea Rendimentos", "fii"), "CPTS11": ("Capitânia Securities", "fii"),
    "HGRU11": ("CSHG Renda Urbana", "fii"), "XPML11": ("XP Malls", "fii"),
    "VILG11": ("Vinci Logística", "fii"), "JSRE11": ("JS Real Estate", "fii"),
    "BRCO11": ("Bresco Logística", "fii"), "LVBI11": ("VBI Logística", "fii"),
    "MALL11": ("Malls Brasil Plural", "fii"), "HSML11": ("HSI Malls", "fii"),
    "TRXF11": ("TRX Real Estate", "fii"), "ALZR11": ("Alianza Trust", "fii"),
    "IRDM11": ("Iridium Recebíveis", "fii"), "RECR11": ("REC Recebíveis", "fii"),
    "CRI11": ("Cartesia Recebíveis", "fii"),
    # ETFs
    "BOVA11": ("iShares Ibovespa", "etf"), "IVVB11": ("iShares S&P 500", "etf"),
    "SMAL11": ("iShares Small Caps", "etf"), "XFIX11": ("XP Fixa", "etf"),
    "HASH11": ("Hashdex Cripto", "etf"), "BOVV11": ("Itaú Ibovespa", "etf"),
    "ISUS11": ("iShares Sustentabilidade", "etf"), "ECOL11": ("Trend ESG", "etf"),
    "GOVE11": ("Trend Governança", "etf"), "MATB11": ("Trend Materiais", "etf"),
    "IMAB11": ("Itaú IMA-B", "etf"), "IRIB11": ("Itaú IRF-M", "etf"),
    "DIVO11": ("Itaú Dividendos", "etf"), "PIBB11": ("PIBB", "etf"),
    "XINA11": ("XP China", "etf"), "NASD11": ("Trend Nasdaq", "etf"),
    "AURO11": ("Trend Ouro", "etf"),
}

CRYPTO_NAMES = {
    "BTC": "Bitcoin", "ETH": "Ethereum", "SOL": "Solana", "XRP": "XRP",
    "ADA": "Cardano", "DOGE": "Dogecoin", "BNB": "BNB", "USDT": "Tether",
    "USDC": "USD Coin", "AVAX": "Avalanche", "DOT": "Polkadot",
    "LINK": "Chainlink", "LTC": "Litecoin", "BCH": "Bitcoin Cash",
}

# Bancos/instituições para CDB específico: (alias, nome, exige maiúscula?)
CDB_BANKS: tuple[tuple[str, str, bool], ...] = (
    ("nubank", "Nubank", False),
    ("itau", "Itaú", False),
    ("bradesco", "Bradesco", False),
    ("santander", "Santander", False),
    ("banco do brasil", "Banco do Brasil", False),
    ("caixa economica", "Caixa", False),
    ("Caixa", "Caixa", True),
    ("btg pactual", "BTG Pactual", False),
    ("XP", "XP", True),
    ("inter", "Inter", False),
    ("c6", "C6 Bank", False),
    ("sicredi", "Sicredi", False),
    ("sicoob", "Sicoob", False),
    ("daycoval", "Daycoval", False),
    ("bmg", "BMG", False),
    ("sofisa", "Sofisa", False),
    ("banco original", "Banco Original", False),
    ("Original", "Banco Original", True),
    ("banco pan", "Banco Pan", False),
    ("banco safra", "Safra", False),
    ("Safra", "Safra", True),
    ("banco master", "Banco Master", False),
    ("Master", "Banco Master", True),
    ("will bank", "Will Bank", False),
    ("neon", "Neon", False),
    ("picpay", "PicPay", False),
    ("mercado pago", "Mercado Pago", False),
    ("pagbank", "PagBank", False),
    ("banrisul", "Banrisul", False),
    ("brb", "BRB", False),
)

FIXED_INCOME = (
    ("tesouro selic", "fixed_income:tesouro-selic", "Tesouro Selic"),
    ("tesouro ipca", "fixed_income:tesouro-ipca", "Tesouro IPCA+"),
    ("tesouro prefixado", "fixed_income:tesouro-prefixado", "Tesouro Prefixado"),
    ("tesouro direto", "fixed_income:tesouro-direto", "Tesouro Direto"),
    ("cdb", "fixed_income:cdb", "CDB"),
    ("lci", "fixed_income:lci", "LCI"),
    ("lca", "fixed_income:lca", "LCA"),
    ("cri", "fixed_income:cri", "CRI"),
    ("cra", "fixed_income:cra", "CRA"),
    ("debentures", "fixed_income:debenture", "Debêntures"),
    ("debenture", "fixed_income:debenture", "Debênture"),
    ("renda fixa", "fixed_income:renda-fixa", "Renda fixa"),
    ("poupanca", "fixed_income:poupanca", "Poupança"),
)

# Indícios de que a notícia é sobre CDB/oferta, mesmo sem a palavra "CDB" no título.
CDB_CUE_RE = re.compile(
    r"\b(cdb|cdi|renda fixa|prefixado|pos-fixado|liquidez|lci|lca|rentabilidade|rende(?:m|ndo)?)\b"
)

# alias normalizado -> (ticker ou None, nome, classe, cnpj)
COMPANIES: tuple[tuple[str, str, str, str, str | None], ...] = (
    ("petrobras", "PETR4", "Petrobras", "acao", "33.000.167/0001-01"),
    ("petroleo brasileiro", "PETR4", "Petrobras", "acao", "33.000.167/0001-01"),
    ("vale s.a.", "VALE3", "Vale", "acao", "33.592.510/0001-54"),
    ("vale3", "VALE3", "Vale", "acao", "33.592.510/0001-54"),
    ("itau", "ITUB4", "Itaú Unibanco", "acao", "60.872.504/0001-23"),
    ("bradesco", "BBDC4", "Bradesco", "acao", "60.746.948/0001-12"),
    ("banco do brasil", "BBAS3", "Banco do Brasil", "acao", "00.000.000/0001-91"),
    ("ambev", "ABEV3", "Ambev", "acao", "07.526.557/0001-00"),
    ("weg", "WEGE3", "WEG", "acao", "84.429.695/0001-11"),
    ("magazine luiza", "MGLU3", "Magazine Luiza", "acao", "47.960.950/0001-21"),
    ("magalu", "MGLU3", "Magazine Luiza", "acao", "47.960.950/0001-21"),
    ("suzano", "SUZB3", "Suzano", "acao", "16.404.287/0001-55"),
    ("eletrobras", "ELET3", "Eletrobras", "acao", "00.001.180/0001-26"),
    ("gerdau", "GGBR4", "Gerdau", "acao", "33.611.500/0001-19"),
    ("csn", "CSNA3", "CSN", "acao", "33.042.730/0001-04"),
    ("localiza", "RENT3", "Localiza", "acao", "16.670.085/0001-55"),
    ("raia drogasil", "RADL3", "Raia Drogasil", "acao", "61.585.865/0001-51"),
    ("lojas renner", "LREN3", "Lojas Renner", "acao", "92.754.738/0001-62"),
    ("telefonica brasil", "VIVT3", "Vivo", "acao", "02.558.157/0001-62"),
    ("totvs", "TOTS3", "Totvs", "acao", "53.113.791/0001-22"),
    ("hapvida", "HAPV3", "Hapvida", "acao", "21.623.012/0001-60"),
    ("rumo", "RAIL3", "Rumo", "acao", "02.387.241/0001-60"),
    ("santander brasil", "SANB11", "Santander Brasil", "acao", "90.400.888/0001-42"),
    ("btg pactual", "BPAC11", "BTG Pactual", "acao", "30.306.294/0001-45"),
    ("braskem", "BRKM5", "Braskem", "acao", "42.150.391/0001-70"),
    ("klabin", "KLBN11", "Klabin", "acao", "89.637.490/0001-45"),
    ("embraer", "EMBR3", "Embraer", "acao", "07.689.002/0001-89"),
    ("ultrapar", "UGPA3", "Ultrapar", "acao", "33.256.439/0001-39"),
    ("usiminas", "USIM5", "Usiminas", "acao", "60.894.730/0001-05"),
    ("copel", "CPLE6", "Copel", "acao", "76.483.817/0001-20"),
    ("sabesp", "SBSP3", "Sabesp", "acao", "43.776.517/0001-80"),
    ("cemig", "CMIG4", "Cemig", "acao", "17.155.730/0001-64"),
    ("engie brasil", "ENGI11", "Engie Brasil", "acao", "02.474.103/0001-19"),
    ("prio", "PRIO3", "PRIO", "acao", "10.629.105/0001-68"),
    ("3r petroleum", "RRRP3", "3R Petroleum", "acao", "11.087.501/0001-08"),
    ("minerva", None, "Minerva Foods", "acao", "67.620.377/0001-14"),
    ("marfrig", "MRFG3", "Marfrig", "acao", "03.853.896/0001-40"),
    ("brf", "BRFS3", "BRF", "acao", "01.838.723/0001-27"),
    ("jbs", "JBSS3", "JBS", "acao", "02.916.265/0001-60"),
    ("azul linhas", "AZUL4", "Azul", "acao", "09.305.994/0001-29"),
    ("gol linhas", "GOLL4", "Gol", "acao", "06.164.253/0001-87"),
    ("cvc brasil", "CVCB3", "CVC Brasil", "acao", "10.760.260/0001-19"),
)


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value)
    return text.encode("ascii", "ignore").decode("ascii").lower()


def _digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


def _slug(value: str) -> str:
    normalized = _normalize(value)
    return re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")


def _infer_ticker(symbol: str) -> AssetMention:
    if symbol in TICKERS:
        name, asset_class = TICKERS[symbol]
        return AssetMention(
            key=f"ticker:{symbol}",
            name=name,
            asset_class=asset_class,
            confidence=0.95,
        )
    if symbol.endswith("11"):
        return AssetMention(
            key=f"ticker:{symbol}",
            name=symbol,
            asset_class="fundo",
            confidence=0.5,
        )
    if re.search(r"[3-6]$", symbol):
        return AssetMention(
            key=f"ticker:{symbol}",
            name=symbol,
            asset_class="acao",
            confidence=0.6,
        )
    return AssetMention(
        key=f"ticker:{symbol}",
        name=symbol,
        asset_class="outros",
        confidence=0.4,
    )


def extract_assets(
    text: str,
    *,
    issuers: Mapping[str, str] | None = None,
    fixed_income_hint: str | None = None,
) -> list[AssetMention]:
    found: dict[str, AssetMention] = {}

    def add(mention: AssetMention) -> None:
        current = found.get(mention.key)
        if current is None or mention.confidence > current.confidence:
            found[mention.key] = mention

    upper = text.upper()
    normalized = _normalize(text)

    for match in TICKER_RE.finditer(upper):
        add(_infer_ticker(match.group(1)))

    for symbol, name in CRYPTO_NAMES.items():
        if re.search(rf"\b{symbol}\b", upper):
            add(
                AssetMention(
                    key=f"crypto:{symbol}",
                    name=name,
                    asset_class="cripto",
                    confidence=0.6,
                )
            )

    for cnpj in CNPJ_RE.findall(text):
        digits = _digits(cnpj)
        issuer_name = (issuers or {}).get(digits)
        if issuer_name:
            add(
                AssetMention(
                    key=f"issuer:{digits}",
                    name=issuer_name,
                    asset_class="outros",
                    confidence=0.75,
                    cnpj=digits,
                )
            )

    cdb_mentions = 0
    has_cdb_cue = bool(CDB_CUE_RE.search(normalized))
    cdb_context = bool(re.search(r"\bcdb\b", normalized)) or (
        fixed_income_hint == "cdb" and has_cdb_cue
    )
    if cdb_context:
        for alias, bank_name, case_sensitive in CDB_BANKS:
            haystack = text if case_sensitive else normalized
            pattern = rf"\b{re.escape(alias if case_sensitive else _normalize(alias))}\b"
            if re.search(pattern, haystack):
                add(
                    AssetMention(
                        key=f"fixed_income:cdb:{_slug(bank_name)}",
                        name=f"CDB {bank_name}",
                        asset_class="renda_fixa",
                        confidence=0.8,
                    )
                )
                cdb_mentions += 1

    for phrase, key, name in FIXED_INCOME:
        if key == "fixed_income:cdb" and cdb_mentions > 0:
            continue
        if re.search(rf"\b{re.escape(phrase)}\b", normalized):
            add(
                AssetMention(
                    key=key,
                    name=name,
                    asset_class="renda_fixa",
                    confidence=0.75,
                )
            )

    for alias, ticker, name, asset_class, cnpj in COMPANIES:
        if re.search(rf"\b{re.escape(alias)}\b", normalized):
            key = f"ticker:{ticker}" if ticker else f"issuer:{_digits(cnpj or '')}"
            add(
                AssetMention(
                    key=key,
                    name=name,
                    asset_class=asset_class,
                    confidence=0.7,
                    cnpj=_digits(cnpj) if cnpj else None,
                )
            )

    return sorted(found.values(), key=lambda item: item.confidence, reverse=True)
