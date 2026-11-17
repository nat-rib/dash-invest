from src.monitor.extraction import extract_assets


def test_extrai_tickers_classes_e_renda_fixa():
    text = (
        "Petrobras (PETR4) e Vale3 sobem. Tesouro Selic e CDB atraem investidores. "
        "HGLG11 e IVVB11 são alternativas; Bitcoin (BTC) segue volátil."
    )

    assets = {item.key: item for item in extract_assets(text)}

    assert assets["ticker:PETR4"].asset_class == "acao"
    assert assets["ticker:HGLG11"].asset_class == "fii"
    assert assets["ticker:IVVB11"].asset_class == "etf"
    assert assets["fixed_income:tesouro-selic"].asset_class == "renda_fixa"
    assert assets["fixed_income:cdb"].asset_class == "renda_fixa"
    assert assets["crypto:BTC"].asset_class == "cripto"


def test_extrai_cnpj_com_cadastro_de_emissores():
    text = "A companhia 33.000.167/0001-01 divulgou resultados."

    assets = extract_assets(text, issuers={"33000167000101": "PETROLEO BRASILEIRO S.A."})

    assert assets[0].key == "issuer:33000167000101"
    assert assets[0].name == "PETROLEO BRASILEIRO S.A."
    assert assets[0].cnpj == "33000167000101"


def test_ticker_desconhecido_e_inferido_pelo_sufixo():
    assets = {item.key: item for item in extract_assets("A empresa XPTO3 e o fundo XPTO11.")}

    assert assets["ticker:XPTO3"].asset_class == "acao"
    assert assets["ticker:XPTO11"].asset_class == "fundo"


def test_cdb_por_banco_privado():
    text = (
        "CDB do Nubank paga 110% do CDI; o CDB do Banco Master e do Inter "
        "aparecem na lista de melhores taxas."
    )

    assets = {item.key: item for item in extract_assets(text)}

    assert assets["fixed_income:cdb:nubank"].name == "CDB Nubank"
    assert "fixed_income:cdb:banco-master" in assets
    assert "fixed_income:cdb:inter" in assets
    assert "fixed_income:cdb" not in assets


def test_cdb_generico_sem_banco():
    assets = {item.key for item in extract_assets("CDB de liquidez diária rende mais.")}

    assert "fixed_income:cdb" in assets


def test_banco_sem_cdb_nao_gera_produto():
    assets = {item.key for item in extract_assets("Nubank anuncia novo aplicativo.")}

    assert not any(key.startswith("fixed_income:cdb") for key in assets)


def test_hint_de_fonte_cdb_identifica_banco_sem_palavra_cdb():
    assets = {
        item.key: item
        for item in extract_assets(
            "Nubank, Inter e C6 disputam a preferência do investidor.",
            fixed_income_hint="cdb",
        )
    }

    assert assets["fixed_income:cdb:nubank"].name == "CDB Nubank"
    assert "fixed_income:cdb:inter" in assets
    assert "fixed_income:cdb:c6-bank" in assets
