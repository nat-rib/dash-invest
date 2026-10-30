import pandas as pd
import plotly.express as px
import streamlit as st

from src.formatting import money, percent
from src.mortgage import amortize_extra, break_even_net_return, build_sac_schedule, compare_with_investment, savings

st.set_page_config(page_title="Amortizar ou investir", page_icon="⌁", layout="wide")
st.title("Amortizar ou investir")
st.caption("Projeção para financiamento SAC + TR. Valores estimados; confira sempre a simulação e o boleto da CAIXA antes de amortizar.")

with st.sidebar:
    st.header("Financiamento")
    balance = st.number_input("Saldo devedor atual (R$)", min_value=1.0, value=245_135.45, step=1_000.0)
    months = st.number_input("Prazo restante (meses)", min_value=1, value=226, step=1)
    interest = st.number_input("Juros nominais anuais (%)", min_value=0.0, value=10.7447, step=0.01) / 100
    tr = st.number_input("TR anual estimada (%)", min_value=0.0, value=0.0, step=0.01, help="A TR futura é desconhecida; ajuste o cenário se desejar.") / 100
    fees = st.number_input("Seguros e taxas mensais (R$)", min_value=0.0, value=0.0, step=10.0, help="Preencha se souber MIP, DFI e tarifa administrativa.")
    st.header("Decisão")
    extra = st.number_input("Valor para decidir (R$)", min_value=1.0, max_value=float(balance - 0.01), value=8_464.0, step=500.0)
    mode_label = st.radio("Se amortizar", ["Reduzir prazo", "Reduzir parcela"], index=0)
    return_rate = st.number_input("Retorno líquido anual efetivo do investimento (%)", min_value=0.0, value=10.0, step=0.1, help="Informe uma taxa já líquida de IR e custos, compatível com risco e prazo.") / 100

mode = "prazo" if mode_label == "Reduzir prazo" else "parcela"
base = build_sac_schedule(balance, int(months), interest, tr, fees)
alternative = amortize_extra(balance, int(months), interest, tr, extra, mode, fees)
metrics = savings(base, alternative)
comparison = compare_with_investment(base, alternative, extra, return_rate)
break_even = break_even_net_return(base, alternative, extra)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Amortização extra", money(extra))
c2.metric("Juros projetados evitados", money(metrics["interest_saved"]))
c3.metric("Prazo reduzido", f"{int(metrics['months_saved'])} meses")
c4.metric("Decisão no cenário", str(comparison["winner"]), money(abs(float(comparison["difference"]))))
c5.metric("Retorno líquido de equilíbrio", percent(break_even))

if comparison["winner"] == "Investir":
    st.info("Neste cenário matemático, investir gera patrimônio final maior. Isso não mede segurança, liquidez ou risco de o retorno não acontecer.")
else:
    st.info("Neste cenário matemático, amortizar gera patrimônio final maior. Ela também reduz dívida e risco de fluxo de caixa.")

st.caption(
    f"Ao fim dos {int(months)} meses: investir o valor hoje → {money(comparison['invest_value'])}; "
    f"amortizar e investir as parcelas economizadas → {money(comparison['amortization_value'])}."
)
st.caption("Acima da taxa de equilíbrio, investir vence nesta projeção; abaixo dela, amortizar vence.")
st.warning("A comparação supõe retorno líquido constante e reinvestimento das economias. TR, seguros, taxas, impostos e retorno de investimentos podem variar; não é recomendação individual.")

plot = pd.concat([
    base.assign(Cenário="Sem amortização"),
    alternative.assign(Cenário=f"Amortizar — {mode_label.lower()}"),
])
st.plotly_chart(px.line(plot, x="Mês", y="Saldo final", color="Cenário", title="Saldo devedor projetado"), use_container_width=True)

with st.expander("Ver projeções de parcelas"):
    first = st.number_input("Exibir os primeiros meses", min_value=1, max_value=int(months), value=min(24, int(months)))
    left, right = st.columns(2)
    with left:
        st.caption("Sem amortização")
        st.dataframe(base.head(int(first)), use_container_width=True, hide_index=True)
    with right:
        st.caption(f"Com amortização: {mode_label.lower()}")
        st.dataframe(alternative.head(int(first)), use_container_width=True, hide_index=True)
