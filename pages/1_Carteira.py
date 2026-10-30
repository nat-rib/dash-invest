from pathlib import Path
import streamlit as st
from src.importer import load_snapshot
from src.portfolio import positions_frame

st.set_page_config(page_title="Carteira", page_icon="▤", layout="wide")
st.title("Carteira")
path = Path("portfolio.json")
if not path.exists():
    st.info("Importe uma carteira primeiro.")
    st.stop()
try:
    snapshot = load_snapshot(path)
except Exception as error:
    st.error(str(error)); st.stop()
frame = positions_frame(snapshot)
st.sidebar.header("Filtros")
institutions = st.sidebar.multiselect("Instituição", sorted(frame["Instituição"].unique()), default=sorted(frame["Instituição"].unique()))
classes = st.sidebar.multiselect("Classe", sorted(frame["Classe"].unique()), default=sorted(frame["Classe"].unique()))
currencies = st.sidebar.multiselect("Moeda", sorted(frame["Moeda"].unique()), default=sorted(frame["Moeda"].unique()))
filtered = frame[frame["Instituição"].isin(institutions) & frame["Classe"].isin(classes) & frame["Moeda"].isin(currencies)]
st.caption("Campos sem informação permanecem como ‘Não disponível’; eles não são tratados como zero.")
st.dataframe(filtered, use_container_width=True, hide_index=True, column_config={
    "Valor atual": st.column_config.NumberColumn(format="R$ %.2f"),
    "Custo total": st.column_config.NumberColumn(format="R$ %.2f"),
    "Ganho/perda": st.column_config.NumberColumn(format="R$ %.2f"),
    "Rentabilidade": st.column_config.NumberColumn(format="%.2f%%"),
})
