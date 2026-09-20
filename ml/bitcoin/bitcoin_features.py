def build_bitcoin_features(transactions):
    """
    Build basic Bitcoin wallet features
    from normalized Bitcoin transactions.
    """

    transaction_count = len(transactions)

    total_btc_sent = 0.0
    total_btc_received = 0.0

    total_fees = 0.0

    unique_senders = set()
    unique_receivers = set()

    for tx in transactions:

        total_btc_sent += float(
            tx.get("sent_value_satoshi", 0)
        ) / 100000000

        total_btc_received += float(
            tx.get("received_value_satoshi", 0)
        ) / 100000000

        total_fees += float(
            tx.get("fee", 0)
        ) / 100000000

        for sender in tx.get("senders", []):
            unique_senders.add(
                str(sender).lower()
            )

        for receiver in tx.get("receivers", []):
            unique_receivers.add(
                str(receiver).lower()
            )

    average_btc_received = (
        total_btc_received / transaction_count
        if transaction_count > 0
        else 0.0
    )

    average_btc_sent = (
        total_btc_sent / transaction_count
        if transaction_count > 0
        else 0.0
    )

    return {
        "transaction_count": transaction_count,
        "total_btc_sent": total_btc_sent,
        "total_btc_received": total_btc_received,
        "total_btc_balance": (
            total_btc_received - total_btc_sent
        ),
        "total_fees_btc": total_fees,
        "unique_senders": len(unique_senders),
        "unique_receivers": len(unique_receivers),
        "average_btc_sent": average_btc_sent,
        "average_btc_received": average_btc_received,
    }