from pathlib import Path
import streamlit as st
import plotly.express as px

from src.formatting import money
from src.importer import load_snapshot
from src.portfolio import brl_frame, consolidated_total, positions_frame

st.set_page_config(page_title="Minha carteira", page_icon="◈", layout="wide")
st.title("Minha carteira")
st.caption("Visão consolidada, local e sem conexão com instituições financeiras.")

path = Path("portfolio.json")
if not path.exists():
    st.info("Nenhuma carteira carregada. Use a página **Importação** para selecionar um portfolio.json.")
    st.stop()
try:
    snapshot = load_snapshot(path)
except Exception as error:
    st.error(f"Não foi possível abrir portfolio.json: {error}")
    st.stop()

frame = positions_frame(snapshot)
known_brl = brl_frame(frame)
total = consolidated_total(frame)
c1, c2, c3 = st.columns(3)
c1.metric("Patrimônio consolidado", money(total))
c2.metric("Instituições", frame["Instituição"].nunique())
c3.metric("Ativos", len(frame))
st.caption(f"Última atualização: {snapshot.snapshot_date.strftime('%d/%m/%Y')}. Valores em outras moedas só entram no consolidado quando possuem conversão explícita para BRL.")

if known_brl.empty:
    st.warning("Não há posições em BRL com valor conhecido para exibir a composição.")
else:
    left, right = st.columns(2)
    with left:
        by_class = known_brl.groupby("Classe", as_index=False)["Valor consolidado BRL"].sum()
        st.plotly_chart(px.pie(by_class, values="Valor consolidado BRL", names="Classe", title="Composição por classe", hole=.55), use_container_width=True)
    with right:
        by_institution = known_brl.groupby("Instituição", as_index=False)["Valor consolidado BRL"].sum()
        st.plotly_chart(px.bar(by_institution, x="Instituição", y="Valor consolidado BRL", title="Distribuição por instituição"), use_container_width=True)

st.subheader("Posições")
st.dataframe(frame, use_container_width=True, hide_index=True)
