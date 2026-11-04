"""Estilos compartilhados e conservadores para desktop e mobile."""

import streamlit as st


def apply_theme() -> None:
    """Aplica ajustes responsivos sem alterar componentes internos do Streamlit."""
    st.markdown(
        """
        <style>
        .block-container {
            max-width: 1440px;
            padding-top: 1.5rem;
            padding-bottom: 3rem;
        }
        [data-testid="stMetric"] {
            min-width: 0;
            overflow-wrap: anywhere;
        }
        [data-testid="stPlotlyChart"] {
            width: 100%;
        }
        @media (max-width: 640px) {
            .block-container {
                padding: 1rem 0.8rem 2rem;
            }
            [data-testid="stHorizontalBlock"] {
                flex-wrap: wrap;
                gap: 0.75rem;
            }
            [data-testid="stHorizontalBlock"] > [data-testid="column"] {
                flex: 1 1 calc(50% - 0.75rem) !important;
                min-width: 145px !important;
            }
            [data-testid="stDataFrame"],
            [data-testid="stTable"] {
                max-width: 100%;
                overflow-x: auto;
            }
            .stButton > button,
            .stDownloadButton > button {
                min-height: 2.75rem;
            }
            h1 {
                font-size: 1.8rem;
            }
            h2 {
                font-size: 1.4rem;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
