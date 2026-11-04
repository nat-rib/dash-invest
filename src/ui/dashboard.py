"""Dashboard principal; usa o snapshot legado como fonte explicitamente identificada."""

from pathlib import Path
import os

import plotly.express as px
import streamlit as st

from src.formatting import money
from src.importer import load_snapshot
from src.portfolio import brl_frame, consolidated_total, positions_frame


def _quality_summary(frame):
    total = len(frame)
    if total == 0:
        return {"total": 0, "value_known": 0, "cost_known": 0, "converted": 0}
    return {
        "total": total,
        "value_known": int(frame["Valor consolidado BRL"].notna().sum()),
        "cost_known": int(frame["Custo total"].notna().sum()),
        "converted": int(frame["Valor convertido BRL"].notna().sum()),
    }


def render_dashboard() -> None:
    st.title("Visão geral")
    st.caption("Resumo da carteira e qualidade dos dados disponíveis.")

    path = Path(os.getenv("PORTFOLIO_PATH", "portfolio.json"))
    if not path.exists():
        st.info(
            "Nenhum snapshot JSON foi encontrado. Importe sua carteira para começar. "
            "A importação do snapshot não cria transações no ledger."
        )
        st.page_link("pages/3_Importacao.py", label="Importar carteira", icon="↑")
        return

    try:
        snapshot = load_snapshot(path)
    except Exception as error:
        st.error(f"Não foi possível carregar o snapshot da carteira: {error}")
        return

    frame = positions_frame(snapshot)
    st.caption(
        f"Fonte: snapshot JSON · Data-base: {snapshot.snapshot_date:%d/%m/%Y}. "
        "O resumo ainda não combina automaticamente o snapshot com o ledger SQLite."
    )

    if frame.empty:
        st.info("O snapshot foi carregado, mas não contém posições.")
        return

    known_brl = brl_frame(frame)
    total = consolidated_total(frame)
    quality = _quality_summary(frame)

    metrics = st.columns(4)
    metrics[0].metric("Patrimônio conhecido em BRL", money(total))
    metrics[1].metric("Ativos", f"{quality['total']}")
    metrics[2].metric("Instituições", f"{frame['Instituição'].nunique()}")
    metrics[3].metric("Posições com valor em BRL", f"{quality['value_known']}/{quality['total']}")

    st.subheader("Rentabilidade")
    left, right = st.columns(2)
    with left:
        st.metric("TWR / XIRR", "Não consolidada")
        st.caption(
            "Os cálculos estão disponíveis na seção Rentabilidade, mas dependem de "
            "fluxos e avaliações informados. Não são inferidos deste snapshot."
        )
    with right:
        st.metric("Benchmark", "Não configurado")
        st.caption("Ainda não há benchmark associado à carteira nem série comparável.")

    if known_brl.empty:
        st.warning(
            "Não há posições com valor conhecido em BRL. A composição patrimonial "
            "não será estimada a partir de moedas sem conversão explícita."
        )
    else:
        st.subheader("Alocação conhecida")
        by_class = known_brl.groupby("Classe", as_index=False)["Valor consolidado BRL"].sum()
        by_institution = known_brl.groupby("Instituição", as_index=False)["Valor consolidado BRL"].sum()
        charts = st.columns(2)
        with charts[0]:
            st.plotly_chart(
                px.pie(
                    by_class, values="Valor consolidado BRL", names="Classe",
                    title="Por classe de ativo", hole=0.55,
                ),
                use_container_width=True,
                config={"displayModeBar": False},
            )
        with charts[1]:
            st.plotly_chart(
                px.bar(
                    by_institution, x="Instituição", y="Valor consolidado BRL",
                    title="Por instituição",
                ),
                use_container_width=True,
                config={"displayModeBar": False},
            )

        st.subheader("Maiores posições")
        top = known_brl.sort_values("Valor consolidado BRL", ascending=False).head(5)
        for start in range(0, len(top), 2):
            cards = st.columns(2)
            for offset, (_, position) in enumerate(top.iloc[start:start + 2].iterrows()):
                with cards[offset]:
                    with st.container(border=True):
                        st.markdown(f"**{position['Nome']}**")
                        st.caption(
                            f"{position['Ticker'] or 'Sem ticker'} · "
                            f"{position['Instituição']} · {position['Classe']}"
                        )
                        st.metric("Valor conhecido", money(position["Valor consolidado BRL"]))

    st.subheader("Qualidade e cobertura")
    quality_cols = st.columns(3)
    quality_cols[0].metric("Com custo conhecido", f"{quality['cost_known']}/{quality['total']}")
    quality_cols[1].metric("Com conversão explícita", f"{quality['converted']}/{quality['total']}")
    missing = quality["total"] - quality["value_known"]
    quality_cols[2].metric("Sem valor consolidado em BRL", f"{missing}")
    if missing:
        st.info(
            "Posições sem valor em BRL são mantidas como indisponíveis e não entram "
            "no patrimônio consolidado. Confira moeda, preço e conversão no cadastro."
        )

    with st.expander("Ver tabela completa de posições"):
        st.dataframe(frame, use_container_width=True, hide_index=True)
