def analyze_wallet_transactions(wallet_address, transactions):

    wallet_address = wallet_address.lower()

    incoming = []
    outgoing = []

    total_received = 0
    total_sent = 0

    connected_wallets = set()

    for tx in transactions:

        sender = (tx.get("from") or "").lower()
        receiver = (tx.get("to") or "").lower()

        amount = float(tx.get("amount_eth") or 0)

        # Incoming transaction
        if receiver == wallet_address:

            incoming.append(tx)

            total_received += amount

            if sender:
                connected_wallets.add(sender)

        # Outgoing transaction
        if sender == wallet_address:

            outgoing.append(tx)

            total_sent += amount

            if receiver:
                connected_wallets.add(receiver)

    return {
        "incoming_count": len(incoming),
        "outgoing_count": len(outgoing),

        "total_received_eth": total_received,
        "total_sent_eth": total_sent,

        "unique_wallets_interacted": len(connected_wallets),

        "incoming_transactions": incoming,
        "outgoing_transactions": outgoing
    }