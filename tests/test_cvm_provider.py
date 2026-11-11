import io
import zipfile
from decimal import Decimal

import pytest

from src.domain.observations import QualityStatus
from src.providers.cvm import (
    CvmArchive,
    CvmDfpProvider,
    CvmParseError,
    dfp_url,
    parse_document_index,
    parse_issuers,
    parse_statement,
)

DRE_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)
BPA_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)
BPP_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)
INDEX_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;CATEG_DOC;ID_DOC;DT_RECEB;LINK_DOC"
)

CNPJ = "00.000.000/0001-91"
COMPANY = "EMPRESA TESTE S.A."
GROUP_CONSOLIDATED = "DF Consolidado - Demonstração do Resultado"


def dre_csv() -> str:
    return "\n".join(
        [
            DRE_HEADER,
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;{GROUP_CONSOLIDATED};REAL;MIL;ÚLTIMO;2024-01-01;2024-12-31;3.01;Receita;1000.0000000000;S",
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;{GROUP_CONSOLIDATED};REAL;MIL;PENÚLTIMO;2023-01-01;2023-12-31;3.01;Receita;900.0000000000;S",
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;{GROUP_CONSOLIDATED};REAL;MIL;ÚLTIMO;2024-01-01;2024-12-31;3.11;Lucro;100.0000000000;S",
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;{GROUP_CONSOLIDATED};REAL;MIL;ÚLTIMO;2024-01-01;2024-12-31;9.99;Conta livre;5.0000000000;N",
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;{GROUP_CONSOLIDATED};REAL;MIL;ÚLTIMO;2024-01-01;2024-12-31;3.02;Custo;;S",
        ]
    )


def bpa_csv() -> str:
    return "\n".join(
        [
            BPA_HEADER,
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;DF Consolidado - Balanço Patrimonial Ativo;REAL;MIL;ÚLTIMO;2024-12-31;1;Ativo Total;2000.0000000000;S",
        ]
    )


def index_csv() -> str:
    return "\n".join(
        [
            INDEX_HEADER,
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;DFP;144874;2025-02-19;http://example/doc",
        ]
    )


def test_dfp_url_valida_ano():
    assert dfp_url(2024).endswith("/dfp_cia_aberta_2024.zip")
    with pytest.raises(ValueError):
        dfp_url(1990)


def test_parse_statement_normaliza_escala_ordem_e_ausencia():
    observations = parse_statement(dre_csv(), statement="DRE")

    assert len(observations) == 3
    assert [item.metric for item in observations] == [
        "revenue",
        "net_income",
        "cvm_dfp.dre.9.99",
    ]
    assert [item.value for item in observations] == [
        Decimal("1000000.0000000000"),
        Decimal("100000.0000000000"),
        Decimal("5000.0000000000"),
    ]
    assert all(item.currency == "BRL" for item in observations)
    assert all(item.instrument_id == "cnpj:00000000000191" for item in observations)
    assert all(item.period_start is not None and item.period_start.year == 2024 for item in observations)
    assert all(item.quality_status is QualityStatus.VERIFIED for item in observations)


def test_parse_statement_anexa_documento_publicado():
    documents = parse_document_index(index_csv())
    observations = parse_statement(dre_csv(), statement="DRE", documents=documents)

    assert observations[0].source_document == "http://example/doc"
    assert observations[0].published_at is not None
    assert observations[0].published_at.isoformat() == "2025-02-19T00:00:00+00:00"


def test_bpp_mapeia_patrimonio_no_plano_societario():
    bpp = "\n".join(
        [
            BPP_HEADER,
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;DF Consolidado - Balanço Patrimonial Passivo;REAL;MIL;ÚLTIMO;2024-12-31;2.03;Patrimônio Líquido Consolidado;500.0000000000;S",
        ]
    )

    observations = parse_statement(bpp, statement="BPP")

    assert [item.metric for item in observations] == ["equity"]
    assert observations[0].value == Decimal("500000.0000000000")


def test_bpp_mapeia_patrimonio_no_plano_de_instituicao_financeira():
    bpp = "\n".join(
        [
            BPP_HEADER,
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;DF Consolidado - Balanço Patrimonial Passivo;REAL;MIL;ÚLTIMO;2024-12-31;2.03;Provisões;225.0000000000;S",
            f"{CNPJ};2024-12-31;1;{COMPANY};001023;DF Consolidado - Balanço Patrimonial Passivo;REAL;MIL;ÚLTIMO;2024-12-31;2.07;Patrimônio Líquido Consolidado;2567.0000000000;S",
        ]
    )

    observations = parse_statement(bpp, statement="BPP")
    metrics = {item.metric: item.value for item in observations}

    assert metrics["equity"] == Decimal("2567000.0000000000")
    assert metrics["cvm_dfp.bpp.2.03"] == Decimal("225000.0000000000")


def test_parse_statement_respeita_escopo_consolidado():
    individual = dre_csv().replace("Consolidado", "Individual")

    assert parse_statement(individual, statement="DRE", consolidated=True) == []
    assert len(parse_statement(individual, statement="DRE", consolidated=False)) == 3


def test_parse_statement_rejeita_valor_invalido():
    invalid = dre_csv().replace("1000.0000000000", "abc")

    with pytest.raises(CvmParseError):
        parse_statement(invalid, statement="DRE")


def test_archive_le_membro_latin1():
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("amostra.csv", dre_csv().encode("iso-8859-1"))

    text = CvmArchive(buffer.getvalue()).read_text("amostra.csv")

    assert "ÚLTIMO" in text
    assert "Receita" in text


def test_provider_le_zip_sem_rede(monkeypatch):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("dfp_cia_aberta_2024.csv", index_csv().encode("iso-8859-1"))
        archive.writestr("dfp_cia_aberta_DRE_con_2024.csv", dre_csv().encode("iso-8859-1"))
        archive.writestr("dfp_cia_aberta_BPA_con_2024.csv", bpa_csv().encode("iso-8859-1"))
    payload = buffer.getvalue()

    def fake_download(year: int, *, timeout: int = 180) -> bytes:
        assert year == 2024
        return payload

    monkeypatch.setattr("src.providers.cvm.download_dfp", fake_download)

    observations = list(CvmDfpProvider().fetch(2024).observations)

    metrics = {item.metric for item in observations}
    assert {"revenue", "net_income", "total_assets", "cvm_dfp.dre.9.99"} <= metrics
    total_assets = next(item for item in observations if item.metric == "total_assets")
    assert total_assets.value == Decimal("2000000.0000000000")
    assert total_assets.source_document == "http://example/doc"


def test_parse_issuers_deduplica_mantendo_publicacao_mais_recente():
    documents = parse_document_index(
        "\n".join(
            [
                INDEX_HEADER,
                f"{CNPJ};2023-12-31;1;{COMPANY} ANTIGA;001023;DFP;1;2024-02-01;http://example/2023",
                f"{CNPJ};2024-12-31;2;{COMPANY};001023;DFP;2;2025-02-19;http://example/2024",
            ]
        )
    )

    issuers = parse_issuers(documents)

    assert len(issuers) == 1
    assert issuers[0].name == COMPANY
    assert issuers[0].cvm_code == "001023"
    assert issuers[0].updated_at.date().isoformat() == "2025-02-19"
