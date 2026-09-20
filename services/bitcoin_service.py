import requests
import time


BLOCKSTREAM_API_URL = "https://blockstream.info/api"


def get_live_btc_transactions(wallet_address):
    """
    Fetch live Bitcoin transactions from Blockstream Esplora API.
    """

    url = (
        f"{BLOCKSTREAM_API_URL}/address/"
        f"{wallet_address}/txs"
    )

    response = requests.get(
        url,
        timeout=20
    )

    print(
        f"[BITCOIN] HTTP STATUS: {response.status_code}"
    )

    if response.status_code == 200:

        data = response.json()

        if not isinstance(data, list):
            raise Exception(
                "Invalid response from Blockstream API"
            )

        print(
            f"[BITCOIN] Live transactions received: {len(data)}"
        )

        return data

    print(
        "[BITCOIN] Blockstream response:"
    )

    print(
        response.text[:1000]
    )

    raise Exception(
        f"Blockstream API error: "
        f"{response.status_code}"
    )


def get_btc_transactions(wallet_address):
    """
    Fetch live Bitcoin transactions.

    Blockstream is the primary API.
    Demo data is used only if the live API fails.
    """

    try:

        print(
            "=============================================="
        )
        print(
            "[BITCOIN] Fetching LIVE blockchain data..."
        )
        print(
            "=============================================="
        )

        transactions = get_live_btc_transactions(
            wallet_address
        )

        print(
            "[BITCOIN] LIVE DATA SUCCESS"
        )

        return transactions

    except Exception as e:

        print(
            "=============================================="
        )
        print(
            "[BITCOIN] LIVE API FAILED"
        )
        print(
            f"[BITCOIN] Error: {e}"
        )
        print(
            "[BITCOIN] Using LOCAL DEMO data as fallback."
        )
        print(
            "=============================================="
        )

        return get_demo_btc_transactions(
            wallet_address
        )


def normalize_btc_transaction(
    tx,
    wallet_address
):
    """
    Convert Blockstream transaction format
    into the format expected by the application.
    """

    wallet = str(
        wallet_address
    ).lower()

    senders = []
    receivers = []

    total_input_value = 0
    total_output_value = 0

    for vin in tx.get("vin", []):

        prevout = vin.get(
            "prevout"
        ) or {}

        address = prevout.get(
            "scriptpubkey_address"
        )

        value = prevout.get(
            "value",
            0
        )

        if address:

            senders.append(
                address
            )

        total_input_value += int(
            value or 0
        )

    for vout in tx.get("vout", []):

        address = vout.get(
            "scriptpubkey_address"
        )

        value = vout.get(
            "value",
            0
        )

        if address:

            receivers.append(
                address
            )

        total_output_value += int(
            value or 0
        )

    wallet_received_satoshis = 0

    for vout in tx.get("vout", []):

        address = vout.get(
            "scriptpubkey_address"
        )

        if (
            address
            and str(address).lower()
            == wallet
        ):

            wallet_received_satoshis += int(
                vout.get(
                    "value",
                    0
                )
                or 0
            )

    wallet_sent_satoshis = 0

    for vin in tx.get("vin", []):

        prevout = vin.get(
            "prevout"
        ) or {}

        address = prevout.get(
            "scriptpubkey_address"
        )

        if (
            address
            and str(address).lower()
            == wallet
        ):

            wallet_sent_satoshis += int(
                prevout.get(
                    "value",
                    0
                )
                or 0
            )

    status = tx.get(
        "status"
    ) or {}

    block_height = status.get(
        "block_height"
    )

    block_time = status.get(
        "block_time"
    )

    return {
        "hash": tx.get(
            "txid"
        ),

        "txid": tx.get(
            "txid"
        ),

        "from": (
            senders[0]
            if senders
            else None
        ),

        "to": (
            receivers[0]
            if receivers
            else None
        ),

        "senders": senders,

        "receivers": receivers,

        "value_btc": (
            wallet_received_satoshis
            / 100000000
        ),

        "value": (
            wallet_received_satoshis
            / 100000000
        ),

        "value_satoshi": wallet_received_satoshis,

        "sent_value_btc": (
            wallet_sent_satoshis
            / 100000000
        ),

        "total_input_btc": (
            total_input_value
            / 100000000
        ),

        "total_output_btc": (
            total_output_value
            / 100000000
        ),

        "fee_btc": (
            int(
                tx.get(
                    "fee",
                    0
                )
                or 0
            )
            / 100000000
        ),

        "block_height": block_height,

        "timestamp": block_time,

        "confirmed": status.get(
            "confirmed",
            False
        ),

        "raw": tx,
    }


def trace_btc_wallet(
    wallet_address,
    raw_transactions,
    max_hops=3
):
    """
    Build a simple Bitcoin transaction graph
    from the transactions already fetched.

    This version avoids repeatedly calling the
    external API for every address.
    """

    wallet = str(
        wallet_address
    ).lower()

    nodes = {
        wallet_address
    }

    edges = []

    for tx in raw_transactions or []:

        tx_senders = []

        for vin in tx.get(
            "vin",
            []
        ):

            prevout = vin.get(
                "prevout"
            ) or {}

            address = prevout.get(
                "scriptpubkey_address"
            )

            if address:
                tx_senders.append(
                    address
                )

        tx_receivers = []

        for vout in tx.get(
            "vout",
            []
        ):

            address = vout.get(
                "scriptpubkey_address"
            )

            if address:
                tx_receivers.append(
                    address
                )

        for source in tx_senders:

            nodes.add(source)

            for target in tx_receivers:

                nodes.add(target)

                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "tx_hash": tx.get(
                            "txid"
                        ),
                    }
                )

    unique_edges = []

    seen = set()

    for edge in edges:

        key = (
            str(edge["source"]).lower()
            + "->"
            + str(edge["target"]).lower()
            + "->"
            + str(edge.get("tx_hash"))
        )

        if key not in seen:

            seen.add(key)

            unique_edges.append(
                edge
            )

    return {
        "nodes": list(nodes),
        "edges": unique_edges,
        "max_hops": max_hops,
        "wallet": wallet_address,
    }