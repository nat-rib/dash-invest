from pathlib import Path
import streamlit as st
import plotly.express as px
from src.importer import load_snapshot
from src.portfolio import brl_frame, consolidated_total, positions_frame

st.set_page_config(page_title="Análise", page_icon="◔", layout="wide")
st.title("Análise")
st.caption("Um único snapshot descreve a carteira atual; não permite reconstruir desempenho histórico, TWR ou XIRR.")
path = Path("portfolio.json")
if not path.exists(): st.info("Importe uma carteira primeiro."); st.stop()
try: frame = positions_frame(load_snapshot(path))
except Exception as error: st.error(str(error)); st.stop()
data = brl_frame(frame)
if data.empty: st.warning("A análise consolidada requer valores conhecidos em BRL."); st.stop()
total = consolidated_total(frame)
by_class = data.groupby("Classe", as_index=False)["Valor atual"].sum()
by_institution = data.groupby("Instituição", as_index=False)["Valor atual"].sum()
c1, c2 = st.columns(2)
with c1: st.plotly_chart(px.pie(by_class, names="Classe", values="Valor atual", title="Distribuição por classe", hole=.5), use_container_width=True)
with c2: st.plotly_chart(px.pie(by_institution, names="Instituição", values="Valor atual", title="Distribuição por instituição", hole=.5), use_container_width=True)
st.subheader("Maiores posições")
top = data.sort_values("Valor atual", ascending=False).head(10).copy()
top["Concentração"] = top["Valor atual"] / total
st.dataframe(top[["Nome", "Instituição", "Classe", "Valor atual", "Concentração"]], use_container_width=True, hide_index=True)
comparable = data.dropna(subset=["Custo total", "Valor atual"])
if not comparable.empty:
    st.subheader("Custo de aquisição x valor atual")
    plot_data = comparable.melt(id_vars="Nome", value_vars=["Custo total", "Valor atual"], var_name="Medida", value_name="Valor")
    st.plotly_chart(px.bar(plot_data, x="Nome", y="Valor", color="Medida", barmode="group"), use_container_width=True)
else: st.info("Não há posições com custo e valor atual comparáveis.")
