import io
import zipfile
from decimal import Decimal

from src.providers.cvm_itr import CvmItrProvider, itr_url

DRE_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_INI_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)
BPA_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;GRUPO_DFP;MOEDA;ESCALA_MOEDA;"
    "ORDEM_EXERC;DT_FIM_EXERC;CD_CONTA;DS_CONTA;VL_CONTA;ST_CONTA_FIXA"
)
INDEX_HEADER = (
    "CNPJ_CIA;DT_REFER;VERSAO;DENOM_CIA;CD_CVM;CATEG_DOC;ID_DOC;DT_RECEB;LINK_DOC"
)

CNPJ = "00.000.000/0001-91"
COMPANY = "EMPRESA TESTE S.A."
DRE_GROUP = "DF Consolidado - Demonstração do Resultado"


def dre_csv() -> str:
    return "\n".join(
        [
            DRE_HEADER,
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;{DRE_GROUP};REAL;MIL;ÚLTIMO;2024-04-01;2024-06-30;3.01;Receita;1000.0000000000;S",
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;{DRE_GROUP};REAL;MIL;ÚLTIMO;2024-01-01;2024-06-30;3.01;Receita;1900.0000000000;S",
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;{DRE_GROUP};REAL;MIL;PENÚLTIMO;2023-04-01;2023-06-30;3.01;Receita;800.0000000000;S",
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;{DRE_GROUP};REAL;MIL;ÚLTIMO;2024-04-01;2024-06-30;3.11;Lucro;100.0000000000;S",
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;{DRE_GROUP};REAL;MIL;ÚLTIMO;2024-01-01;2024-06-30;3.11;Lucro;190.0000000000;S",
        ]
    )


def bpa_csv() -> str:
    return "\n".join(
        [
            BPA_HEADER,
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;DF Consolidado - Balanço Patrimonial Ativo;REAL;MIL;ÚLTIMO;2024-06-30;1;Ativo Total;5000.0000000000;S",
        ]
    )


def index_csv() -> str:
    return "\n".join(
        [
            INDEX_HEADER,
            f"{CNPJ};2024-06-30;1;{COMPANY};001023;ITR;140502;2024-08-07;http://example/itr",
        ]
    )


def build_payload() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("itr_cia_aberta_2024.csv", index_csv().encode("iso-8859-1"))
        archive.writestr("itr_cia_aberta_DRE_con_2024.csv", dre_csv().encode("iso-8859-1"))
        archive.writestr("itr_cia_aberta_BPA_con_2024.csv", bpa_csv().encode("iso-8859-1"))
    return buffer.getvalue()


def test_itr_url_valida_ano():
    assert itr_url(2024).endswith("/itr_cia_aberta_2024.zip")


def test_provider_separa_trimestre_e_acumulado(monkeypatch):
    payload = build_payload()

    def fake_download(year: int, *, timeout: int = 240) -> bytes:
        assert year == 2024
        return payload

    monkeypatch.setattr("src.providers.cvm_itr.download_itr", fake_download)

    batch = CvmItrProvider().fetch(2024)
    metrics = {item.metric: item for item in batch.observations}

    assert set(metrics) == {
        "revenue",
        "revenue_ytd",
        "net_income",
        "net_income_ytd",
        "total_assets",
    }
    assert metrics["revenue"].value == Decimal("1000000.0000000000")
    assert metrics["revenue"].period_start.isoformat() == "2024-04-01"
    assert metrics["revenue_ytd"].value == Decimal("1900000.0000000000")
    assert metrics["revenue_ytd"].period_start.isoformat() == "2024-01-01"
    assert metrics["total_assets"].period_start is None

    assert all(item.provider == "cvm_itr" for item in batch.observations)
    assert metrics["revenue"].source_document == "http://example/itr"
    assert metrics["revenue"].published_at.isoformat() == "2024-08-07T00:00:00+00:00"

    assert [(item.cnpj, item.name, item.source) for item in batch.issuers] == [
        ("00000000000191", COMPANY, "cvm")
    ]
