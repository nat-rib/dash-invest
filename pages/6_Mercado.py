from pathlib import Path
import os

import plotly.express as px
import streamlit as st

from src.importer import load_snapshot, replace_snapshot
from src.history import record_snapshot
from src.market_data import AlphaVantageClient, MarketDataError, replace_prices, updatable_positions
from src.portfolio import positions_frame

st.set_page_config(page_title="Mercado", page_icon="↗", layout="wide")
st.title("Cotações e histórico")
st.caption("Fonte: Alpha Vantage. Apenas símbolos de negociação são enviados ao provedor; saldos, quantidades e instituições permanecem locais.")
st.info("Chaves gratuitas têm limite de 25 consultas por dia. O painel espera automaticamente entre consultas; atualize somente os ativos necessários.")

path = Path("portfolio.json")
if not path.exists():
    st.info("Importe uma carteira primeiro.")
    st.stop()
snapshot = load_snapshot(path)
api_key = st.secrets.get("ALPHA_VANTAGE_API_KEY", os.getenv("ALPHA_VANTAGE_API_KEY", ""))
if not api_key:
    st.warning("Configure a chave em `.streamlit/secrets.toml`. Use `.streamlit/secrets.example.toml` como modelo.")
    st.stop()
client = AlphaVantageClient(api_key)
positions = updatable_positions(snapshot)
if not positions:
    st.info("Não há posições cotáveis. Preencha `ticker` ou `market_symbol` nas ações, FIIs e ETFs.")
    st.stop()

labels = {index: f"{snapshot.positions[index].name} — {symbol}" for index, symbol in positions}
selected = st.selectbox("Ativo para histórico", list(labels), format_func=labels.get)
symbol = dict(positions)[selected]
if st.button("Carregar histórico diário"):
    try:
        history = client.daily_history_position(snapshot.positions[selected])
        first, last = history.iloc[0], history.iloc[-1]
        change = last["Fechamento"] / first["Fechamento"] - 1
        st.metric("Variação no histórico retornado", f"{change:.2%}", f"Último fechamento: R$ {last['Fechamento']:,.2f}")
        st.plotly_chart(px.line(history, x="Data", y="Fechamento", title=f"Histórico diário — {symbol}"), use_container_width=True)
    except MarketDataError as error:
        st.error(str(error))

st.divider()
st.subheader("Atualizar preços das posições cotáveis")
st.caption("A prévia consulta uma cotação por ativo. Revise os preços e confirme antes de substituir o snapshot local.")
if st.button("Consultar preços atuais"):
    quotes, errors = {}, []
    for index, item_symbol in positions:
        try:
            quotes[index] = client.quote_position(snapshot.positions[index])
        except MarketDataError as error:
            errors.append(f"{labels[index]}: {error}")
    fx_rates = {}
    for currency in {snapshot.positions[index].currency for index in quotes if snapshot.positions[index].currency != "BRL"}:
        try:
            fx_rates[currency] = client.crypto_quote(currency, "BRL")
        except MarketDataError as error:
            errors.append(f"Conversão {currency}/BRL: {error}")
    st.session_state["alpha_quotes"] = quotes
    st.session_state["alpha_fx_rates"] = fx_rates
    st.session_state["alpha_errors"] = errors
    if quotes:
        preview = replace_prices(snapshot, quotes, fx_rates)
        record_snapshot(preview, source="alpha_vantage")
        st.success("Snapshot de preços registrado no histórico local.")

quotes = st.session_state.get("alpha_quotes", {})
for error in st.session_state.get("alpha_errors", []):
    st.warning(error)
if quotes:
    preview = replace_prices(snapshot, quotes, st.session_state.get("alpha_fx_rates", {}))
    st.dataframe(positions_frame(preview), use_container_width=True, hide_index=True)
    confirmed = st.checkbox("Confirmo que desejo substituir os preços atuais no portfolio.json.")
    if st.button("Salvar preços atualizados", type="primary", disabled=not confirmed):
        replace_snapshot(path, preview.model_dump_json(indent=2).encode())
        st.success("Snapshot atualizado localmente. Registros sem cotação permaneceram inalterados.")

if st.button("Registrar snapshot atual sem consultar a API"):
    record_snapshot(snapshot, source="manual")
    st.success("Snapshot atual registrado no histórico local.")
