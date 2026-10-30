import plotly.express as px
import streamlit as st

from src.history import portfolio_history, position_history

st.set_page_config(page_title="Histórico", page_icon="⌁", layout="wide")
st.title("Histórico patrimonial")
st.caption("Snapshots são armazenados somente em `data/portfolio_history.db` neste Mac.")
history = portfolio_history()
if history.empty:
    st.info("Ainda não há snapshots. Consulte preços em **Mercado** ou registre o snapshot atual para iniciar o histórico.")
    st.stop()

st.plotly_chart(px.line(history, x="Data", y="Patrimônio BRL", markers=True, title="Patrimônio consolidado em BRL"), use_container_width=True)
if len(history) > 1:
    change = history.iloc[-1]["Patrimônio BRL"] / history.iloc[0]["Patrimônio BRL"] - 1
    st.metric("Variação entre primeiro e último snapshot", f"{change:.2%}")
st.warning("Isto é variação de valor, não rentabilidade da carteira: aportes, retiradas, impostos e proventos alteram o patrimônio. Para TWR ou XIRR, será necessário registrar fluxos de caixa.")

positions = position_history()
if not positions.empty:
    choices = sorted(positions["Posição"].unique())
    selected = st.selectbox("Posição", choices)
    selected_history = positions[positions["Posição"] == selected]
    value_column = "Valor BRL" if selected_history["Valor BRL"].notna().any() else "Valor atual"
    st.plotly_chart(px.line(selected_history, x="Data", y=value_column, markers=True, title="Evolução da posição"), use_container_width=True)
