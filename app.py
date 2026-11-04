import streamlit as st

from src.ui.dashboard import render_dashboard
from src.ui.theme import apply_theme


st.set_page_config(
    page_title="Dash Invest",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)
apply_theme()

navigation = st.navigation(
    {
        "Visão geral": [
            st.Page(render_dashboard, title="Visão geral", icon="🏠", default=True),
        ],
        "Minha carteira": [
            st.Page("pages/1_Carteira.py", title="Posições", icon="▤"),
            st.Page("pages/4_Detalhes.py", title="Detalhes do ativo", icon="◉"),
            st.Page("pages/8_Ledger.py", title="Ledger e operações", icon="⇄"),
            st.Page("pages/9_Rentabilidade.py", title="Rentabilidade", icon="%"),
        ],
        "Investigar": [
            st.Page("pages/2_Analise.py", title="Análise da carteira", icon="◔"),
            st.Page("pages/5_Amortizacao.py", title="Amortizar ou investir", icon="⌁"),
        ],
        "Mercado": [
            st.Page("pages/6_Mercado.py", title="Cotações", icon="↗"),
            st.Page("pages/7_Historico.py", title="Histórico patrimonial", icon="⌁"),
        ],
        "Configurações": [
            st.Page("pages/3_Importacao.py", title="Importar carteira", icon="↑"),
        ],
    },
    position="sidebar",
)
navigation.run()
