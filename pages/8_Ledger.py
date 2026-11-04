"""Ledger: migração explícita do snapshot e importação/reconciliação de extratos."""
import csv
from io import StringIO
import os
from pathlib import Path

import streamlit as st

from src.domain.models import AssetClass, Instrument
from src.domain.reconciliation import reconcile_transfers
from src.importers.broker_csv import BrokerCsvMapping, adapt_broker_csv
from src.importers.transactions_csv import CanonicalTransactionCsvImporter
from src.importer import load_snapshot
from src.persistence.database import SQLiteDatabase
from src.persistence.repositories import (
    InstrumentRepository, PortfolioPositionRepository, PortfolioRepository,
    TransactionRepository, TransferLinkRepository,
)
from src.persistence.snapshot_import import PortfolioSnapshotImporter


st.set_page_config(page_title="Ledger e operações", page_icon="⇄", layout="wide")
st.title("Ledger e operações")
st.caption("Importação controlada, histórico auditável e conciliação explícita de transferências.")

portfolio_path = Path(os.getenv("PORTFOLIO_PATH", "portfolio.json"))
database = SQLiteDatabase()
database.initialize()
portfolios = PortfolioRepository(database)
instruments = InstrumentRepository(database)
positions = PortfolioPositionRepository(database)
transactions = TransactionRepository(database)
transfer_links = TransferLinkRepository(database)

tab_migration, tab_csv, tab_reconciliation = st.tabs(
    ["Migrar carteira JSON", "Importar extrato CSV", "Conciliar transferências"]
)

with tab_migration:
    st.subheader("Migrar snapshot legado para SQLite")
    st.write(
        "A migração cria/atualiza cadastro de ativos e posições de referência. "
        "Não cria transações fictícias e não apaga nem substitui o portfolio.json."
    )
    if not portfolio_path.exists():
        st.warning(f"Arquivo legado não encontrado: {portfolio_path}")
    else:
        try:
            snapshot = load_snapshot(portfolio_path)
            st.success(
                f"Snapshot válido: {len(snapshot.positions)} posições, "
                f"data-base {snapshot.snapshot_date:%d/%m/%Y}."
            )
            st.dataframe(
                [{
                    "Instituição": item.institution, "Ativo": item.ticker or item.name,
                    "Classe": item.asset_class, "Quantidade": str(item.quantity) if item.quantity is not None else "—",
                    "Moeda": item.currency,
                } for item in snapshot.positions],
                use_container_width=True, hide_index=True,
            )
            if st.button("Migrar snapshot para SQLite", type="primary"):
                result = PortfolioSnapshotImporter(database).import_snapshot(snapshot)
                st.success(
                    f"Migração concluída: {result.instruments_saved} instrumentos e "
                    f"{result.positions_saved} posições. Transações criadas: 0."
                )
                st.info("O JSON original foi preservado. A migração pode ser repetida com segurança.")
        except Exception as error:
            st.error(f"Não foi possível validar/migrar o snapshot: {error}")

    with st.expander("Estado do banco"):
        st.write("Carteiras:", [item.model_dump(mode="json") for item in portfolios.list_all()])
        st.write("Instrumentos cadastrados:", len(instruments.list_all()))
        st.write("Snapshots persistidos:", len(positions.list_snapshots("legacy-import")))

with tab_csv:
    st.subheader("Adaptar extrato CSV da instituição")
    st.write(
        "Como cada corretora possui seu próprio layout, selecione as colunas do arquivo. "
        "O adaptador normaliza datas, decimais e tipos de operação antes de chamar o importador canônico."
    )
    uploaded = st.file_uploader("Arquivo CSV", type=["csv"], key="broker_csv")
    if uploaded is not None:
        raw = uploaded.getvalue().decode("utf-8-sig")
        delimiter = st.selectbox("Separador", [",", ";", "\\t"], index=1, format_func=lambda x: "TAB" if x == "\\t" else x)
        try:
            reader = csv.DictReader(StringIO(raw), delimiter=delimiter)
            headers = list(reader.fieldnames or [])
            rows = list(reader)
            if not headers:
                st.error("CSV sem cabeçalho.")
                st.stop()
            st.caption(f"{len(rows)} linhas encontradas.")
            st.dataframe(rows[:10], use_container_width=True, hide_index=True)
            with st.expander("Cadastrar instrumento que ainda não existe no catálogo"):
                new_ticker = st.text_input("Ticker / código externo", key="new_instrument_ticker")
                new_name = st.text_input("Nome do ativo", key="new_instrument_name")
                new_class = st.selectbox("Classe do ativo", list(AssetClass), format_func=lambda item: item.value, key="new_instrument_class")
                new_currency = st.selectbox("Moeda do ativo", ["BRL", "USD", "EUR", "GBP", "JPY"], key="new_instrument_currency")
                new_exchange = st.text_input("Bolsa / mercado (opcional)", key="new_instrument_exchange")
                if st.button("Cadastrar instrumento", key="create_instrument"):
                    if not new_ticker.strip() or not new_name.strip():
                        st.error("Informe ticker e nome.")
                    else:
                        try:
                            duplicate = any(
                                item.currency == new_currency and item.asset_class == new_class
                                and (item.exchange or "").casefold() == new_exchange.strip().casefold()
                                and new_ticker.strip().casefold() in {
                                    value.casefold() for value in item.provider_symbols.values()
                                }
                                for item in instruments.list_all()
                            )
                            if duplicate:
                                st.error("Já existe um instrumento com esse ticker em algum provedor.")
                            else:
                                instruments.save(Instrument(
                                    name=new_name.strip(), asset_class=new_class,
                                    currency=new_currency, exchange=new_exchange.strip() or None,
                                    provider_symbols={"broker_ticker": new_ticker.strip()},
                                ))
                                st.success("Instrumento cadastrado. Atualize a página para associá-lo ao extrato.")
                                st.rerun()
                        except Exception as error:
                            st.error(f"Não foi possível cadastrar: {error}")

            inst_list = instruments.list_all()
            if not inst_list:
                st.warning("Cadastre ou migre instrumentos antes de importar compras/vendas.")
            labels = {
                f"{item.name} · {item.asset_class.value} · {item.currency} · {item.id[:8]}": item.id
                for item in inst_list
            }
            with st.form("broker_csv_mapping"):
                institution = st.text_input("Instituição / corretora")
                currency = st.selectbox("Moeda padrão", ["BRL", "USD", "EUR", "GBP", "JPY"])
                decimal_locale = st.selectbox("Formato numérico", ["pt_BR", "en_US"])
                date_format = st.text_input("Formato da data quando não for ISO-8601", "%d/%m/%Y")
                timezone_name = st.text_input("Timezone para datas sem fuso", "America/Sao_Paulo")

                def column_picker(label, key, required=False):
                    options = ["(não mapear)"] + headers
                    default = headers.index(key) + 1 if key in headers else 0
                    selected = st.selectbox(label, options, index=default, key=f"map_{key}")
                    if required and selected == "(não mapear)":
                        st.warning(f"Mapeie a coluna: {label}.")
                    return "" if selected == "(não mapear)" else selected

                st.markdown("**Mapeamento de colunas**")
                column_mapping = {
                    "external_id": column_picker("ID externo da operação (opcional)", "external_id"),
                    "occurred_at": column_picker("Data da operação", "occurred_at", True),
                    "transaction_type": column_picker("Tipo da operação", "transaction_type", True),
                    "instrument_id": column_picker("Ticker / código do ativo", "instrument_id"),
                    "quantity": column_picker("Quantidade", "quantity"),
                    "unit_price": column_picker("Preço unitário", "unit_price"),
                    "amount": column_picker("Valor bruto / valor da transferência", "amount"),
                    "fees": column_picker("Taxas", "fees"),
                    "taxes": column_picker("Impostos", "taxes"),
                    "currency": column_picker("Moeda por linha (opcional)", "currency"),
                    "sequence": column_picker("Sequência (opcional)", "sequence"),
                    "transfer_id": column_picker("ID da transferência (opcional)", "transfer_id"),
                    "notes": column_picker("Observações (opcional)", "notes"),
                }
                asset_column = column_mapping["instrument_id"]
                instrument_map = {}
                if asset_column:
                    asset_values = sorted({(row.get(asset_column) or "").strip() for row in rows if (row.get(asset_column) or "").strip()})
                    if asset_values and not inst_list:
                        st.warning("Sem instrumentos no catálogo, não será possível importar compras/vendas.")
                    for raw_asset in asset_values:
                        selected_label = st.selectbox(
                            f"Associar {raw_asset}",
                            ["(não associado)"] + list(labels),
                            key=f"asset_{raw_asset}",
                        )
                        if selected_label != "(não associado)":
                            instrument_map[raw_asset] = labels[selected_label]
                submitted = st.form_submit_button("Validar e importar operações", type="primary")
            if submitted:
                if not institution.strip():
                    st.error("Informe a instituição.")
                elif not portfolios.get("legacy-import"):
                    st.error("Migre primeiro o snapshot JSON para criar a carteira SQLite.")
                else:
                    mapping = BrokerCsvMapping(
                        institution=institution, currency=currency, columns=column_mapping,
                        instrument_map=instrument_map, delimiter=delimiter,
                        decimal_locale=decimal_locale, date_format=date_format,
                        timezone_name=timezone_name,
                    )
                    try:
                        result = adapt_broker_csv(
                            raw, portfolio_id="legacy-import", mapping=mapping,
                            importer=CanonicalTransactionCsvImporter(transactions),
                        )
                        st.success(
                            f"Importação concluída: {result.inserted} novas operações; "
                            f"{result.skipped_duplicates} duplicadas ignoradas."
                        )
                    except Exception as error:
                        st.error(f"Importação rejeitada sem gravação parcial: {error}")
        except Exception as error:
            st.error(f"Não foi possível ler o CSV: {error}")

with tab_reconciliation:
    st.subheader("Revisar transferências entre instituições")
    events = transactions.list_for_portfolio("legacy-import")
    links = transfer_links.list_for_portfolio("legacy-import")
    linked_ids = {item.transfer_out_id for item in links} | {item.transfer_in_id for item in links}
    pending_events = [event for event in events if event.id not in linked_ids]
    result = reconcile_transfers(pending_events)
    st.metric("Transferências confirmadas manualmente", len(links))
    if result.suggested_pairs:
        st.write("Sugestões com correspondência única. Confirme somente após conferir os dados do extrato.")
        by_id = {event.id: event for event in pending_events}
        for pair in result.suggested_pairs:
            out, incoming = by_id[pair.transfer_out_id], by_id[pair.transfer_in_id]
            left, right, action = st.columns([2, 2, 1])
            left.write(f"**Saída — {out.institution}**")
            left.caption(f"{out.occurred_at:%d/%m/%Y} · {out.amount} {out.currency}")
            right.write(f"**Entrada — {incoming.institution}**")
            right.caption(f"{incoming.occurred_at:%d/%m/%Y} · {incoming.amount} {incoming.currency}")
            if action.button("Confirmar", key=f"confirm_{out.id}_{incoming.id}"):
                try:
                    transfer_links.confirm(out.id, incoming.id)
                    st.success("Pareamento registrado sem alterar os eventos originais.")
                    st.rerun()
                except Exception as error:
                    st.error(f"Não foi possível confirmar: {error}")
    else:
        st.info("Nenhum par único pendente foi encontrado.")
    if result.ambiguous_transaction_ids:
        st.warning(f"{len(result.ambiguous_transaction_ids)} operações possuem mais de uma correspondência possível; exigem revisão manual.")
    if result.unmatched_transaction_ids:
        st.caption(f"{len(result.unmatched_transaction_ids)} transferências sem correspondência candidata.")
    st.divider()
    st.subheader("Pareamento manual")
    st.caption(
        "Use esta opção para resolver casos ambíguos ou com diferenças explicáveis no extrato. "
        "A confirmação fica registrada separadamente e não modifica as transações."
    )
    outgoing = [event for event in pending_events if event.transaction_type.value == "TRANSFER_OUT"]
    incoming_events = [event for event in pending_events if event.transaction_type.value == "TRANSFER_IN"]
    if outgoing and incoming_events:
        out_labels = {
            f"{event.institution} · {event.occurred_at:%d/%m/%Y} · {event.amount} {event.currency} · {event.id[:8]}": event.id
            for event in outgoing
        }
        in_labels = {
            f"{event.institution} · {event.occurred_at:%d/%m/%Y} · {event.amount} {event.currency} · {event.id[:8]}": event.id
            for event in incoming_events
        }
        manual_left, manual_right = st.columns(2)
        selected_out_label = manual_left.selectbox("Transferência de saída", list(out_labels))
        selected_in_label = manual_right.selectbox("Transferência de entrada", list(in_labels))
        if st.button("Confirmar pareamento manual", type="primary", key="manual_transfer_confirm"):
            try:
                transfer_links.confirm(
                    out_labels[selected_out_label], in_labels[selected_in_label],
                    confirmation_source="manual_review",
                )
                st.success("Pareamento manual registrado.")
                st.rerun()
            except Exception as error:
                st.error(f"Não foi possível confirmar o pareamento: {error}")
    else:
        st.caption("Não há duas pontas pendentes disponíveis para pareamento manual.")

    if links:
        st.subheader("Pareamentos confirmados")
        st.dataframe([
            {"Saída": link.transfer_out_id, "Entrada": link.transfer_in_id,
             "Confirmado em": link.linked_at.isoformat(), "Origem": link.confirmation_source}
            for link in links
        ], use_container_width=True, hide_index=True)
