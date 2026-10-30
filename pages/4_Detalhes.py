from pathlib import Path
import streamlit as st
from src.importer import load_snapshot
from src.portfolio import positions_frame
from src.formatting import money, number, percent

st.set_page_config(page_title="Detalhes", page_icon="◉", layout="wide")
st.title("Detalhes do ativo")
path = Path("portfolio.json")
if not path.exists(): st.info("Importe uma carteira primeiro."); st.stop()
try: frame = positions_frame(load_snapshot(path))
except Exception as error: st.error(str(error)); st.stop()
frame["Seleção"] = frame.apply(lambda row: f"{row['Nome']} — {row['Instituição']}", axis=1)
selection = st.selectbox("Ativo", frame["Seleção"])
row = frame.loc[frame["Seleção"] == selection].iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Valor atual", money(row["Valor atual"], row["Moeda"]))
c2.metric("Ganho/perda não realizado", money(row["Ganho/perda"], row["Moeda"]))
c3.metric("Rentabilidade não realizada", percent(row["Rentabilidade"]))
c4.metric("Valor convertido", money(row["Valor convertido BRL"], "BRL"))
st.subheader(row["Nome"])
details = {
    "Instituição": row["Instituição"], "Classe": row["Classe"], "Ticker": row["Ticker"],
    "Moeda": row["Moeda"], "Quantidade": number(row["Quantidade"]),
    "Preço médio": money(row["Preço médio"], row["Moeda"]), "Custo da operação": money(row["Custo da operação"], row["Moeda"]), "Preço atual": money(row["Preço atual"], row["Moeda"]),
    "Custo total": money(row["Custo total"], row["Moeda"]), "Indexador": row["Indexador"],
    "Taxa de conversão": money(row["Taxa de conversão BRL"], "BRL"), "Data da conversão": row["Data da conversão"],
    "Vencimento": row["Vencimento"], "Data de referência": row["Referência"],
    "Data de aplicação": row["Data de aplicação"], "Emissor": row["Emissor"],
    "Taxa anual": percent(row["Taxa anual"] / 100 if row["Taxa anual"] is not None else None),
    "Valor aplicado informado": money(row["Valor aplicado informado"], row["Moeda"]),
    "Categoria de risco": row["Categoria de risco"], "Liquidez": row["Liquidez"],
    "Observações": row["Observações"],
}
st.table({"Campo": list(details), "Valor": ["Não disponível" if value is None else value for value in details.values()]})
