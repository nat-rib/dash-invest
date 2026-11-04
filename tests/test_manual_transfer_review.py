def test_manual_transfer_confirmation_can_accept_amount_difference(repositories):
    transactions, links = repositories
    out = _transfer("out-manual", TransactionType.TRANSFER_OUT, "Broker A", amount="100")
    incoming = _transfer("in-manual", TransactionType.TRANSFER_IN, "Broker B", amount="99.50")
    transactions.append_many([out, incoming])
    link = links.confirm(out.id, incoming.id, confirmation_source="manual_review")
    assert link.confirmation_source == "manual_review"
    assert link.transfer_out_id == out.id
    assert link.transfer_in_id == incoming.id
