import requests

BLOCKCHAIN_API_URL = "https://blockchain.info/rawaddr/"


def get_btc_transactions(wallet_address):

    url = f"{BLOCKCHAIN_API_URL}{wallet_address}"

    max_retries = 3

    for attempt in range(max_retries):

        try:

            response = requests.get(
                url,
                timeout=30
            )

        except requests.RequestException as e:

            if attempt == max_retries - 1:
                raise Exception(
                    f"Bitcoin API request failed: {e}"
                )

            import time
            time.sleep(2)

            continue

        if response.status_code == 200:

            data = response.json()

            return data.get("txs", [])

        if response.status_code == 429:

            if attempt == max_retries - 1:
                raise Exception(
                    "Bitcoin API rate limit reached. "
                    "Please try again after a short wait."
                )

            import time

            wait_time = 3 * (attempt + 1)

            print(
                f"Bitcoin API rate limited. "
                f"Retrying in {wait_time} seconds..."
            )

            time.sleep(wait_time)

            continue

        raise Exception(
            f"Bitcoin API error: "
            f"{response.status_code} - "
            f"{response.text[:500]}"
        )

    raise Exception(
        "Bitcoin API request failed after retries."
    )

def trace_btc_wallet(wallet_address, transactions, max_hops=3):

    wallet_address = wallet_address.lower().strip()

    MAX_WALLETS_PER_HOP = 10
    MAX_TRANSACTIONS_PER_WALLET = 50

    nodes = [
        {
            "id": wallet_address,
            "address": wallet_address,
            "hop": 0
        }
    ]

    edges = []

    known_nodes = {
        wallet_address
    }

    processed_wallets = {
        wallet_address
    }

    current_level = [
        wallet_address
    ]

    def add_node(address, hop):

        address = address.lower().strip()

        if not address:
            return False

        if address in known_nodes:
            return False

        known_nodes.add(address)

        nodes.append(
            {
                "id": address,
                "address": address,
                "hop": hop
            }
        )

        return True

    def add_edge(source, target, tx_hash):

        source = source.lower().strip()
        target = target.lower().strip()

        if not source or not target:
            return

        if source == target:
            return

        edge_key = (
            source,
            target,
            tx_hash
        )

        existing_keys = {
            (
                str(edge.get("source", "")).lower(),
                str(edge.get("target", "")).lower(),
                edge.get("transaction_hash")
            )
            for edge in edges
        }

        if edge_key in existing_keys:
            return

        edges.append(
            {
                "source": source,
                "target": target,

                # Keep old names for compatibility
                "from": source,
                "to": target,

                "transaction_hash": tx_hash
            }
        )

    # ------------------------------------------------------------
    # HOP 1
    # Use the transactions already fetched for the main wallet.
    # ------------------------------------------------------------

    for tx in transactions[:MAX_TRANSACTIONS_PER_WALLET]:

        if not isinstance(tx, dict):
            continue

        inputs = tx.get("inputs", [])
        outputs = tx.get("out", [])

        connected_addresses = set()

        for item in inputs:

            prev_out = item.get(
                "prev_out",
                {}
            )

            address = prev_out.get("addr")

            if address:
                connected_addresses.add(
                    address.lower().strip()
                )

        for item in outputs:

            address = item.get("addr")

            if address:
                connected_addresses.add(
                    address.lower().strip()
                )

        for address in connected_addresses:

            if address == wallet_address:
                continue

            if len(
                [
                    n for n in nodes
                    if n["hop"] == 1
                ]
            ) >= MAX_WALLETS_PER_HOP:
                break

            add_node(
                address,
                1
            )

            add_edge(
                wallet_address,
                address,
                tx.get("hash")
            )

    # ------------------------------------------------------------
    # HOP 2 + HOP 3
    # Fetch transactions for newly discovered wallets.
    # ------------------------------------------------------------

    for hop in range(2, max_hops + 1):

        previous_level = [
            node["address"]
            for node in nodes
            if node["hop"] == hop - 1
        ]

        previous_level = [
            address
            for address in previous_level
            if address not in processed_wallets
        ]

        previous_level = previous_level[
            :MAX_WALLETS_PER_HOP
        ]

        next_level = []

        for address in previous_level:

            processed_wallets.add(
                address
            )

            try:

                raw_transactions = get_btc_transactions(
                    address
                )

            except Exception as e:

                print(
                    f"Bitcoin trace error for {address}: {e}"
                )

                continue

            for tx in raw_transactions[
                :MAX_TRANSACTIONS_PER_WALLET
            ]:

                if not isinstance(tx, dict):
                    continue

                inputs = tx.get(
                    "inputs",
                    []
                )

                outputs = tx.get(
                    "out",
                    []
                )

                connected_addresses = set()

                for item in inputs:

                    prev_out = item.get(
                        "prev_out",
                        {}
                    )

                    connected_address = prev_out.get(
                        "addr"
                    )

                    if connected_address:

                        connected_addresses.add(
                            connected_address.lower().strip()
                        )

                for item in outputs:

                    connected_address = item.get(
                        "addr"
                    )

                    if connected_address:

                        connected_addresses.add(
                            connected_address.lower().strip()
                        )

                for connected_address in connected_addresses:

                    if connected_address == address:
                        continue

                    # Only add new wallets.
                    if connected_address not in known_nodes:

                        if len(next_level) >= MAX_WALLETS_PER_HOP:
                            break

                        added = add_node(
                            connected_address,
                            hop
                        )

                        if added:
                            next_level.append(
                                connected_address
                            )

                    # Add edge only when both nodes
                    # are already represented in graph.
                    if connected_address in known_nodes:

                        add_edge(
                            address,
                            connected_address,
                            tx.get("hash")
                        )

                if len(next_level) >= MAX_WALLETS_PER_HOP:
                    break

            if len(next_level) >= MAX_WALLETS_PER_HOP:
                break

        current_level = next_level

        if not current_level:
            break

    return {
        "nodes": nodes,
        "edges": edges,
        "max_hops": max_hops
    }
    
def normalize_btc_transaction(tx, wallet_address):
    """
    Convert a Bitcoin transaction into a simplified
    format that our fraud-analysis system can understand.
    """

    wallet_address = wallet_address.lower()

    inputs = tx.get("inputs", [])
    outputs = tx.get("out", [])

    sent_value = 0
    received_value = 0

    senders = []
    receivers = []

    # Process inputs
    for item in inputs:
        prev_out = item.get("prev_out", {})
        address = prev_out.get("addr")
        value = prev_out.get("value", 0)

        if address:
            senders.append(address)

        if address and address.lower() == wallet_address:
            sent_value += value

    # Process outputs
    for item in outputs:
        address = item.get("addr")
        value = item.get("value", 0)

        if address:
            receivers.append(address)

        if address and address.lower() == wallet_address:
            received_value += value

    return {
        "hash": tx.get("hash"),
        "from": senders[0] if senders else None,
        "to": receivers[0] if receivers else None,
        "value": sent_value if sent_value > 0 else received_value,
        "value_btc": (
            sent_value if sent_value > 0 else received_value
        ) / 100000000,
        "timestamp": tx.get("time"),
        "fee": tx.get("fee", 0),
        "block_number": tx.get("block_height"),
        "blockchain": "bitcoin",
        "sent_value_satoshi": sent_value,
        "received_value_satoshi": received_value,
        "senders": senders,
        "receivers": receivers,
    }    