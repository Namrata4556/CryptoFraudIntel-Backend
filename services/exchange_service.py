import json
import os


# ============================================================
# EXCHANGE DATABASE CONFIGURATION
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))
)

EXCHANGE_FILE = os.path.join(
    BASE_DIR,
    "data",
    "exchange_addresses.json"
)


# ============================================================
# EXCHANGE LOOKUP CACHE
# ============================================================

EXCHANGE_LOOKUP_CACHE = None


# ============================================================
# NORMALIZE ADDRESS
# ============================================================

def normalize_address(address):
    """
    Normalize an Ethereum address for comparison.
    """

    if not address:
        return ""

    return str(address).strip().lower()


# ============================================================
# LOAD EXCHANGE DATABASE
# ============================================================

def load_exchange_addresses():
    """
    Load known cryptocurrency exchange addresses.

    Expected JSON structure:

    {
        "Binance": {
            "addresses": [
                "0x..."
            ]
        },
        "Coinbase": {
            "addresses": [
                "0x..."
            ]
        }
    }
    """

    if not os.path.exists(EXCHANGE_FILE):

        print(
            f"[EXCHANGE] Database not found: "
            f"{EXCHANGE_FILE}"
        )

        return {}

    try:

        # utf-8-sig handles both:
        # normal UTF-8
        # UTF-8 files with BOM
        with open(
            EXCHANGE_FILE,
            "r",
            encoding="utf-8-sig"
        ) as file:

            data = json.load(file)

        if not isinstance(data, dict):

            print(
                "[EXCHANGE] Invalid database format."
            )

            return {}

        print(
            f"[EXCHANGE] Loaded "
            f"{len(data)} exchange records."
        )

        return data

    except json.JSONDecodeError as e:

        print(
            f"[EXCHANGE] Invalid JSON database: {e}"
        )

        return {}

    except Exception as e:

        print(
            f"[EXCHANGE] Failed to load database: "
            f"{type(e).__name__}: {e}"
        )

        return {}


# ============================================================
# BUILD EXCHANGE ADDRESS LOOKUP
# ============================================================

def build_exchange_lookup():
    """
    Convert exchange database into:

        normalized_address -> exchange_name

    Example:

        {
            "0x28c6...": "Binance",
            "0x5038...": "Coinbase"
        }

    Supports the current JSON structure:

        "Binance": {
            "addresses": [...]
        }

    Also supports a simple list structure:

        "Binance": [...]
    """

    global EXCHANGE_LOOKUP_CACHE

    # --------------------------------------------------------
    # RETURN CACHE IF ALREADY BUILT
    # --------------------------------------------------------

    if EXCHANGE_LOOKUP_CACHE is not None:

        return EXCHANGE_LOOKUP_CACHE

    # --------------------------------------------------------
    # LOAD DATABASE
    # --------------------------------------------------------

    database = load_exchange_addresses()

    lookup = {}

    # --------------------------------------------------------
    # BUILD LOOKUP
    # --------------------------------------------------------

    for exchange_name, exchange_data in database.items():

        addresses = []

        # ----------------------------------------------------
        # CURRENT STRUCTURE
        #
        # "Binance": {
        #     "addresses": [...]
        # }
        # ----------------------------------------------------

        if isinstance(exchange_data, dict):

            addresses = exchange_data.get(
                "addresses",
                []
            )

        # ----------------------------------------------------
        # ALSO SUPPORT:
        #
        # "Binance": [...]
        # ----------------------------------------------------

        elif isinstance(exchange_data, list):

            addresses = exchange_data

        # ----------------------------------------------------
        # INVALID STRUCTURE
        # ----------------------------------------------------

        else:

            continue

        # ----------------------------------------------------
        # SAFETY CHECK
        # ----------------------------------------------------

        if not isinstance(addresses, list):

            continue

        # ----------------------------------------------------
        # ADD ADDRESSES TO LOOKUP
        # ----------------------------------------------------

        for address in addresses:

            normalized = normalize_address(
                address
            )

            if not normalized:

                continue

            lookup[normalized] = exchange_name

    # --------------------------------------------------------
    # SAVE CACHE
    # --------------------------------------------------------

    EXCHANGE_LOOKUP_CACHE = lookup

    print(
        f"[EXCHANGE] Address lookup size: "
        f"{len(lookup)}"
    )

    return lookup


# ============================================================
# CLEAR EXCHANGE LOOKUP CACHE
# ============================================================

def clear_exchange_lookup_cache():
    """
    Clear cached exchange lookup.

    Useful when exchange_addresses.json
    is modified while backend is running.
    """

    global EXCHANGE_LOOKUP_CACHE

    EXCHANGE_LOOKUP_CACHE = None

    print(
        "[EXCHANGE] Exchange lookup cache cleared."
    )


# ============================================================
# IDENTIFY SINGLE EXCHANGE ADDRESS
# ============================================================

def identify_exchange(address):
    """
    Check whether a single Ethereum address
    belongs to a known exchange.
    """

    normalized = normalize_address(
        address
    )

    if not normalized:

        return None

    lookup = build_exchange_lookup()

    exchange_name = lookup.get(
        normalized
    )

    if not exchange_name:

        return None

    return {

        "identified": True,

        "exchange": exchange_name,

        "address": normalized,

        "confidence": "HIGH"

    }


# ============================================================
# GET TRANSACTION VALUE IN ETH
# ============================================================

def get_transaction_value_eth(transaction):
    """
    Safely extract transaction value in ETH.

    Supports:

        value_eth
        value
    """

    if not isinstance(
        transaction,
        dict
    ):

        return 0.0

    # --------------------------------------------------------
    # BACKEND MAY ALREADY PROVIDE ETH
    # --------------------------------------------------------

    if "value_eth" in transaction:

        try:

            return float(
                transaction.get(
                    "value_eth",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            return 0.0

    # --------------------------------------------------------
    # OTHERWISE TRY RAW WEI
    # --------------------------------------------------------

    value = transaction.get(
        "value",
        0
    )

    try:

        return (
            float(
                value
                or 0
            )
            / 10**18
        )

    except (
        ValueError,
        TypeError
    ):

        return 0.0


# ============================================================
# CHECK SINGLE TRANSACTION
# ============================================================

def check_transaction_exchange_interaction(
    transaction,
    wallet_address
):
    """
    Check whether the analyzed wallet directly
    interacted with a known cryptocurrency exchange.

    Valid interactions:

        WALLET -> EXCHANGE
        EXCHANGE -> WALLET

    IMPORTANT:
    We do NOT count unrelated transactions
    involving an exchange address elsewhere.
    """

    # --------------------------------------------------------
    # SAFETY CHECK
    # --------------------------------------------------------

    if not isinstance(
        transaction,
        dict
    ):

        return None

    wallet_address = normalize_address(
        wallet_address
    )

    sender = normalize_address(
        transaction.get(
            "from"
        )
    )

    receiver = normalize_address(
        transaction.get(
            "to"
        )
    )

    if not sender and not receiver:

        return None

    # --------------------------------------------------------
    # LOAD CACHED LOOKUP
    # --------------------------------------------------------

    lookup = build_exchange_lookup()

    sender_exchange = lookup.get(
        sender
    )

    receiver_exchange = lookup.get(
        receiver
    )

    # --------------------------------------------------------
    # TRANSACTION VALUE
    # --------------------------------------------------------

    value_eth = get_transaction_value_eth(
        transaction
    )

    # --------------------------------------------------------
    # TRANSACTION HASH
    # --------------------------------------------------------

    transaction_hash = (
        transaction.get("hash")
        or transaction.get("transactionHash")
        or transaction.get("tx_hash")
    )

    # --------------------------------------------------------
    # TIMESTAMP
    # --------------------------------------------------------

    timestamp = (
        transaction.get("timestamp")
        or transaction.get("timeStamp")
        or transaction.get("block_timestamp")
    )

    # ========================================================
    # WALLET -> EXCHANGE
    # ========================================================

    if (
        wallet_address
        and sender == wallet_address
        and receiver_exchange
    ):

        return {

            "interaction":
                "SENT_TO_EXCHANGE",

            "exchange":
                receiver_exchange,

            "exchange_address":
                receiver,

            "wallet_address":
                wallet_address,

            "transaction_hash":
                transaction_hash,

            "value_eth":
                value_eth,

            "timestamp":
                timestamp,

            "confidence":
                "HIGH"

        }

    # ========================================================
    # EXCHANGE -> WALLET
    # ========================================================

    if (
        wallet_address
        and receiver == wallet_address
        and sender_exchange
    ):

        return {

            "interaction":
                "RECEIVED_FROM_EXCHANGE",

            "exchange":
                sender_exchange,

            "exchange_address":
                sender,

            "wallet_address":
                wallet_address,

            "transaction_hash":
                transaction_hash,

            "value_eth":
                value_eth,

            "timestamp":
                timestamp,

            "confidence":
                "HIGH"

        }

    # --------------------------------------------------------
    # IMPORTANT:
    #
    # DO NOT classify:
    #
    # exchange -> another wallet
    # another wallet -> exchange
    #
    # unless the analyzed wallet is one side.
    # --------------------------------------------------------

    return None


# ============================================================
# NORMALIZE TRANSACTION INPUT
# ============================================================

def normalize_transactions(transactions):
    """
    Convert different transaction structures
    into a clean list of dictionaries.

    Supported:

    1. List of transaction dictionaries

    2. {
           "result": [...]
       }

    3. {
           "transactions": [...]
       }

    4. {
           "0xhash1": {...},
           "0xhash2": {...}
       }
    """

    if transactions is None:

        return []

    # --------------------------------------------------------
    # ALREADY A LIST
    # --------------------------------------------------------

    if isinstance(
        transactions,
        list
    ):

        valid_transactions = []

        for transaction in transactions:

            if isinstance(
                transaction,
                dict
            ):

                valid_transactions.append(
                    transaction
                )

        return valid_transactions

    # --------------------------------------------------------
    # DICTIONARY
    # --------------------------------------------------------

    if isinstance(
        transactions,
        dict
    ):

        # ----------------------------------------------------
        # ETHERSCAN-STYLE RESPONSE
        # ----------------------------------------------------

        result = transactions.get(
            "result"
        )

        if isinstance(
            result,
            list
        ):

            return [
                item
                for item in result
                if isinstance(
                    item,
                    dict
                )
            ]

        # ----------------------------------------------------
        # INTERNAL BACKEND STRUCTURE
        # ----------------------------------------------------

        transaction_list = transactions.get(
            "transactions"
        )

        if isinstance(
            transaction_list,
            list
        ):

            return [
                item
                for item in transaction_list
                if isinstance(
                    item,
                    dict
                )
            ]

        # ----------------------------------------------------
        # DICTIONARY KEYED BY TRANSACTION HASH
        # ----------------------------------------------------

        values = list(
            transactions.values()
        )

        if (
            values
            and all(
                isinstance(
                    item,
                    dict
                )
                for item in values
            )
        ):

            return values

        return []

    # --------------------------------------------------------
    # UNEXPECTED TYPE
    # --------------------------------------------------------

    print(
        "[EXCHANGE] Unsupported transaction "
        f"type: {type(transactions).__name__}"
    )

    return []


# ============================================================
# IDENTIFY EXCHANGE INTERACTIONS
# ============================================================

def identify_exchange_interactions(
    transactions,
    wallet_address
):
    """
    Analyze all wallet transactions and identify
    direct known cryptocurrency exchange interactions.

    Returns:

        exchange_found
        exchange_count
        exchanges
        interactions
    """

    # --------------------------------------------------------
    # NORMALIZE INPUT
    # --------------------------------------------------------

    transactions = normalize_transactions(
        transactions
    )

    wallet_address = normalize_address(
        wallet_address
    )

    print(
        f"[EXCHANGE] Processing "
        f"{len(transactions)} transactions "
        f"for wallet {wallet_address}"
    )

    # --------------------------------------------------------
    # EMPTY TRANSACTION LIST
    # --------------------------------------------------------

    if not transactions:

        return {

            "exchange_found":
                False,

            "exchange_count":
                0,

            "message":
                "No transactions available "
                "for exchange analysis.",

            "exchanges":
                [],

            "interactions":
                []

        }

    # --------------------------------------------------------
    # BUILD LOOKUP ONCE
    # --------------------------------------------------------

    lookup = build_exchange_lookup()

    print(
        f"[EXCHANGE] Known exchange addresses: "
        f"{len(lookup)}"
    )

    # --------------------------------------------------------
    # PROCESS TRANSACTIONS
    # --------------------------------------------------------

    interactions = []

    seen_transactions = set()

    for transaction in transactions:

        # ----------------------------------------------------
        # DEFENSIVE TYPE CHECK
        # ----------------------------------------------------

        if not isinstance(
            transaction,
            dict
        ):

            print(
                "[EXCHANGE] Skipping invalid "
                "transaction type: "
                f"{type(transaction).__name__}"
            )

            continue

        # ----------------------------------------------------
        # CHECK EXCHANGE INTERACTION
        # ----------------------------------------------------

        result = check_transaction_exchange_interaction(
            transaction,
            wallet_address
        )

        if not result:

            continue

        # ----------------------------------------------------
        # TRANSACTION HASH
        # ----------------------------------------------------

        transaction_hash = result.get(
            "transaction_hash"
        )

        # ----------------------------------------------------
        # DUPLICATE PROTECTION
        # ----------------------------------------------------

        if transaction_hash:

            normalized_hash = str(
                transaction_hash
            ).lower()

            if normalized_hash in seen_transactions:

                continue

            seen_transactions.add(
                normalized_hash
            )

        # ----------------------------------------------------
        # STORE INTERACTION
        # ----------------------------------------------------

        interactions.append(
            result
        )

    # ========================================================
    # NO EXCHANGE FOUND
    # ========================================================

    if not interactions:

        return {

            "exchange_found":
                False,

            "exchange_count":
                0,

            "message":
                "No known cryptocurrency exchange "
                "was identified in the wallet transactions.",

            "exchanges":
                [],

            "interactions":
                []

        }

    # ========================================================
    # GROUP INTERACTIONS BY EXCHANGE
    # ========================================================

    exchange_map = {}

    for interaction in interactions:

        exchange_name = interaction.get(
            "exchange"
        )

        if not exchange_name:

            continue

        # ----------------------------------------------------
        # CREATE EXCHANGE RECORD
        # ----------------------------------------------------

        if exchange_name not in exchange_map:

            exchange_map[
                exchange_name
            ] = {

                "exchange":
                    exchange_name,

                "exchange_address":
                    interaction.get(
                        "exchange_address"
                    ),

                "interaction_count":
                    0,

                "sent_to_exchange":
                    0,

                "received_from_exchange":
                    0,

                "other_interactions":
                    0,

                "total_value_eth":
                    0.0,

                "transactions":
                    []

            }

        exchange_data = exchange_map[
            exchange_name
        ]

        # ----------------------------------------------------
        # INTERACTION COUNT
        # ----------------------------------------------------

        exchange_data[
            "interaction_count"
        ] += 1

        interaction_type = interaction.get(
            "interaction"
        )

        # ----------------------------------------------------
        # SENT
        # ----------------------------------------------------

        if (
            interaction_type
            == "SENT_TO_EXCHANGE"
        ):

            exchange_data[
                "sent_to_exchange"
            ] += 1

        # ----------------------------------------------------
        # RECEIVED
        # ----------------------------------------------------

        elif (
            interaction_type
            == "RECEIVED_FROM_EXCHANGE"
        ):

            exchange_data[
                "received_from_exchange"
            ] += 1

        # ----------------------------------------------------
        # OTHER
        # ----------------------------------------------------

        else:

            exchange_data[
                "other_interactions"
            ] += 1

        # ----------------------------------------------------
        # TOTAL ETH
        # ----------------------------------------------------

        try:

            exchange_data[
                "total_value_eth"
            ] += float(
                interaction.get(
                    "value_eth",
                    0
                )
                or 0
            )

        except (
            ValueError,
            TypeError
        ):

            pass

        # ----------------------------------------------------
        # STORE TRANSACTION
        # ----------------------------------------------------

        exchange_data[
            "transactions"
        ].append(
            interaction
        )

    # ========================================================
    # FINAL EXCHANGE LIST
    # ========================================================

    exchanges = [
        exchange
        for exchange in exchange_map.values()
        if int(
            exchange.get(
                "interaction_count",
                0
            )
            or 0
        ) > 0
    ]

    # ========================================================
    # SAFETY CHECK
    # ========================================================

    if not exchanges:

        return {

            "exchange_found":
                False,

            "exchange_count":
                0,

            "message":
                "No known cryptocurrency exchange "
                "was identified in the wallet transactions.",

            "exchanges":
                [],

            "interactions":
                []

        }

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "exchange_found":
            True,

        "exchange_count":
            len(exchanges),

        "message":
            "Known cryptocurrency exchange "
            "interaction identified.",

        "exchanges":
            exchanges,

        "interactions":
            interactions

    }


# ============================================================
# IDENTIFY EXCHANGES FROM GRAPH
# ============================================================

def identify_exchanges_from_graph(
    graph
):
    """
    Search all nodes in a traced wallet graph
    for known exchange addresses.

    Unlike direct wallet transaction analysis,
    graph analysis CAN identify an exchange
    several hops away.
    """

    if not isinstance(
        graph,
        dict
    ):

        return []

    nodes = graph.get(
        "nodes",
        []
    )

    edges = graph.get(
        "edges",
        []
    )

    if not isinstance(
        nodes,
        list
    ):

        nodes = []

    if not isinstance(
        edges,
        list
    ):

        edges = []

    # --------------------------------------------------------
    # BUILD / USE CACHED LOOKUP
    # --------------------------------------------------------

    lookup = build_exchange_lookup()

    results = []

    seen = set()

    # ========================================================
    # CHECK GRAPH NODES
    # ========================================================

    for node in nodes:

        if not isinstance(
            node,
            dict
        ):

            continue

        address = normalize_address(
            node.get(
                "address"
            )
            or node.get(
                "id"
            )
        )

        if not address:

            continue

        exchange_name = lookup.get(
            address
        )

        if not exchange_name:

            continue

        if address in seen:

            continue

        seen.add(
            address
        )

        hop = node.get(
            "hop",
            0
        )

        # ----------------------------------------------------
        # FIND CONNECTIONS
        # ----------------------------------------------------

        connections = []

        for edge in edges:

            if not isinstance(
                edge,
                dict
            ):

                continue

            source = normalize_address(
                edge.get(
                    "source"
                )
            )

            target = normalize_address(
                edge.get(
                    "target"
                )
            )

            if (
                source == address
                or target == address
            ):

                connections.append({

                    "source":
                        source,

                    "target":
                        target,

                    "transaction_hash":
                        edge.get(
                            "transaction_hash"
                        ),

                    "value_eth":
                        edge.get(
                            "value_eth",
                            0
                        ),

                    "timestamp":
                        edge.get(
                            "timestamp"
                        )

                })

        # ----------------------------------------------------
        # ONLY CONSIDER EXCHANGE NODE IF IT
        # HAS A GRAPH CONNECTION
        # ----------------------------------------------------

        if len(connections) == 0:

            continue

        # ----------------------------------------------------
        # CONFIDENCE
        # ----------------------------------------------------

        if isinstance(
            hop,
            int
        ):

            confidence = (
                "HIGH"
                if hop <= 2
                else "MEDIUM"
            )

        else:

            confidence = "MEDIUM"

        # ----------------------------------------------------
        # ADD EXCHANGE RESULT
        # ----------------------------------------------------

        results.append({

            "exchange":
                exchange_name,

            "exchange_address":
                address,

            "hop":
                hop,

            "confidence":
                confidence,

            "interaction_count":
                len(connections),

            "connections":
                connections

        })

    return results


# ============================================================
# GENERATE GRAPH EXCHANGE SUMMARY
# ============================================================

def generate_exchange_summary(
    graph,
    root_wallet
):
    """
    Generate presentation-friendly exchange
    identification result for a wallet graph.
    """

    exchanges = identify_exchanges_from_graph(
        graph
    )

    root_wallet = normalize_address(
        root_wallet
    )

    # ========================================================
    # NO EXCHANGE FOUND
    # ========================================================

    if not exchanges:

        return {

            "exchange_found":
                False,

            "exchange_count":
                0,

            "message":
                "No known cryptocurrency exchange "
                "was identified in the traced wallet network.",

            "exchanges":
                [],

            "root_wallet":
                root_wallet

        }

    # ========================================================
    # EXCHANGE FOUND
    # ========================================================

    return {

        "exchange_found":
            True,

        "message":
            "Known cryptocurrency exchange "
            "connection identified in the traced wallet network.",

        "root_wallet":
            root_wallet,

        "exchange_count":
            len(exchanges),

        "exchanges":
            exchanges

    }