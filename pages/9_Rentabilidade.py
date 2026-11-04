"""Ferramentas determinísticas de rentabilidade TWR e XIRR."""
from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st

from src.domain.performance import (
    TwrPeriod, calculate_twr, calculate_xirr, external_cash_flows,
)
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import PortfolioRepository, TransactionRepository


st.set_page_config(page_title="Rentabilidade", page_icon="%", layout="wide")
st.title("Rentabilidade da carteira")
st.caption("TWR remove o efeito dos fluxos externos; XIRR mede a taxa anualizada sob a ótica do investidor.")

database = SQLiteDatabase()
database.initialize()
portfolio = PortfolioRepository(database).get("legacy-import")
if portfolio is None:
    st.info("Migre primeiro o snapshot JSON na página **Ledger e operações**.")
    st.stop()

transactions = TransactionRepository(database).list_for_portfolio("legacy-import")
st.caption(f"Carteira: {portfolio.name} · Moeda-base: {portfolio.base_currency}")
flows = external_cash_flows(transactions, currency=portfolio.base_currency)
st.subheader("Fluxos externos identificados no ledger")
if flows:
    st.dataframe([
        {"Data": flow.date, "Fluxo do investidor": float(flow.amount), "Moeda": portfolio.base_currency}
        for flow in flows
    ], use_container_width=True, hide_index=True)
else:
    st.info("Ainda não há aportes ou retiradas registrados. Transferências internas e proventos não são tratados como fluxos externos.")

st.subheader("XIRR — retorno ponderado pelo dinheiro")
st.write(
    "Aportes são fluxos negativos, retiradas são positivos e o patrimônio atual entra como valor terminal. "
    "O cálculo usa as datas reais e base anual de 365 dias."
)
terminal_col, date_col = st.columns(2)
with terminal_col:
    terminal_value = st.number_input(
        f"Patrimônio final ({portfolio.base_currency})",
        min_value=0.0, value=0.0, step=100.0, format="%.2f",
    )
with date_col:
    terminal_date = st.date_input("Data da avaliação final", value=date.today())
if st.button("Calcular XIRR", type="primary"):
    try:
        rate = calculate_xirr(
            flows, terminal_value=Decimal(str(terminal_value)), terminal_date=terminal_date,
        )
        st.metric("XIRR anualizada", f"{float(rate):.2%}")
    except Exception as error:
        st.warning(f"XIRR indisponível: {error}")

st.divider()
st.subheader("TWR — retorno ponderado pelo tempo")
st.write(
    "Informe avaliações consecutivas da carteira. O valor final de cada período deve ser observado "
    "imediatamente após o fluxo externo ocorrido no fim daquele período. Aporte é positivo; retirada é negativa. "
    "Use sempre a mesma moeda-base."
)
template = pd.DataFrame(columns=[
    "start_date", "end_date", "start_value", "end_value_after_flows", "net_external_flow",
])
periods_frame = st.data_editor(
    template, num_rows="dynamic", use_container_width=True, key="twr_periods",
    column_config={
        "start_date": st.column_config.DateColumn("Início"),
        "end_date": st.column_config.DateColumn("Fim"),
        "start_value": st.column_config.NumberColumn("Valor inicial", min_value=0.01, format="%.2f"),
        "end_value_after_flows": st.column_config.NumberColumn("Valor final após fluxos", min_value=0.0, format="%.2f"),
        "net_external_flow": st.column_config.NumberColumn("Fluxo líquido (+ aporte / - retirada)", format="%.2f"),
    },
)
if st.button("Calcular TWR"):
    try:
        periods = []
        for _, row in periods_frame.iterrows():
            if pd.isna(row["start_date"]) or pd.isna(row["end_date"]):
                continue
            periods.append(TwrPeriod(
                start_date=pd.to_datetime(row["start_date"]).date(),
                end_date=pd.to_datetime(row["end_date"]).date(),
                start_value=Decimal(str(row["start_value"])),
                end_value_after_flows=Decimal(str(row["end_value_after_flows"])),
                net_external_flow=Decimal(str(row["net_external_flow"])),
            ))
        result = calculate_twr(periods)
        st.metric("TWR acumulado", f"{float(result.rate):.2%}")
        st.caption(f"{result.periods} períodos · {result.start_date:%d/%m/%Y} a {result.end_date:%d/%m/%Y}")
    except Exception as error:
        st.warning(f"TWR indisponível: {error}")

st.info(
    "Limitação importante: TWR só é confiável quando as avaliações delimitam corretamente os fluxos externos. "
    "O app não estima cotações nem inventa valores intermediários. Fluxos em moedas diferentes exigem conversão cambial explícita."
)
