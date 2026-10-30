from pathlib import Path
import streamlit as st
from src.importer import replace_snapshot, validate_json, validation_messages
from src.portfolio import duplicate_positions, positions_frame

st.set_page_config(page_title="Importação", page_icon="↑", layout="wide")
st.title("Importar carteira")
st.caption("A importação substitui o snapshot inteiro. O arquivo é tratado exclusivamente como dados JSON.")
uploaded = st.file_uploader("Selecione portfolio.json", type=["json"])
if uploaded is None:
    st.info("Selecione um JSON para validar antes de confirmar a substituição.")
    st.stop()
try:
    snapshot = validate_json(uploaded.getvalue())
except Exception as error:
    st.error("O arquivo não passou na validação.")
    for message in validation_messages(error): st.write(f"• {message}")
    st.stop()

st.success(f"Arquivo válido: {len(snapshot.positions)} posições em {snapshot.snapshot_date.strftime('%d/%m/%Y')}.")
duplicates = duplicate_positions(snapshot)
if duplicates: st.warning("Possíveis posições duplicadas: " + "; ".join(" / ".join(item) for item in duplicates))
st.subheader("Prévia")
st.dataframe(positions_frame(snapshot), use_container_width=True, hide_index=True)
confirm = st.checkbox("Confirmo que desejo substituir a carteira exibida atualmente.")
if st.button("Substituir carteira", type="primary", disabled=not confirm):
    replace_snapshot(Path("portfolio.json"), uploaded.getvalue())
    st.success("Carteira substituída com sucesso.")
