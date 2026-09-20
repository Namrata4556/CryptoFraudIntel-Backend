from collections import deque


def build_transaction_graph(transactions):

    nodes = set()
    edges = []

    for tx in transactions:

        sender = (tx.get("from") or "").lower()
        receiver = (tx.get("to") or "").lower()

        if not sender or not receiver:
            continue

        # Add wallets as nodes
        nodes.add(sender)
        nodes.add(receiver)

        # Add transaction as an edge
        edges.append({
            "source": sender,
            "target": receiver,
            "transaction_hash": tx.get("hash"),
            "amount_eth": tx.get("amount_eth"),
            "timestamp": tx.get("timestamp")
        })

    return {
        "nodes": [
            {
                "id": wallet
            }
            for wallet in nodes
        ],
        "edges": edges
    }


def trace_wallet(graph, start_wallet, max_hops=3):

    start_wallet = start_wallet.lower()

    queue = deque()

    queue.append((start_wallet, 0))

    visited = {start_wallet}

    traced_wallets = []

    while queue:

        current_wallet, current_hop = queue.popleft()

        traced_wallets.append({
            "wallet": current_wallet,
            "hop": current_hop
        })

        if current_hop >= max_hops:
            continue

        # Find outgoing transactions
        for edge in graph["edges"]:

            if edge["source"] == current_wallet:

                next_wallet = edge["target"]

                if next_wallet not in visited:

                    visited.add(next_wallet)

                    queue.append(
                        (next_wallet, current_hop + 1)
                    )

    return traced_wallets