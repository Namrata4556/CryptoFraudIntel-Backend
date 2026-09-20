import os
import time
import requests
from dotenv import load_dotenv


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

ETHERSCAN_URL = "https://api.etherscan.io/v2/api"


# ============================================================
# SETTINGS
# ============================================================

MAX_WALLETS_PER_HOP = 3
MAX_TRANSACTIONS_PER_WALLET = 100
MAX_ERC20_TRANSACTIONS = 50
REQUEST_DELAY = 0.10


# ============================================================
# COMMON ETHERSCAN REQUEST
# ============================================================

def etherscan_request(params):
    """Send request to Etherscan V2 API."""

    if not ETHERSCAN_API_KEY:
        raise Exception(
            "ETHERSCAN_API_KEY is missing from the .env file."
        )

    request_params = dict(params)
    request_params["apikey"] = ETHERSCAN_API_KEY

    try:
        response = requests.get(
            ETHERSCAN_URL,
            params=request_params,
            timeout=20
        )

        response.raise_for_status()
        data = response.json()

    except requests.RequestException as e:
        raise Exception(
            f"Failed to connect to Etherscan: {str(e)}"
        )

    status = str(data.get("status", ""))
    result = data.get("result", [])

    if status == "0":

        result_text = str(result).lower()

        if (
            "no transactions" in result_text
            or "no records" in result_text
            or "no transaction" in result_text
        ):
            return []

        message = str(data.get("message", "")).lower()

        if "no transactions" in message:
            return []

        raise Exception(
            f"Etherscan API error: "
            f"{data.get('message', 'Unknown error')} - {result}"
        )

    if not isinstance(result, list):
        raise Exception(
            f"Unexpected Etherscan response: {result}"
        )

    return result


# ============================================================
# ETH TRANSACTIONS
# ============================================================

def get_eth_transactions(
    wallet_address: str,
    page: int = 1,
    offset: int = 100
):
    """
    Fetch normal Ethereum transactions.

    IMPORTANT:
    These are native ETH transactions only.
    ERC20 token transfers are NOT mixed into this result.
    """

    wallet_address = normalize_address(wallet_address)

    params = {
        "chainid": "1",
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": "0",
        "endblock": "99999999",
        "page": str(page),
        "offset": str(offset),
        "sort": "desc"
    }

    return etherscan_request(params)


# ============================================================
# ERC20 TRANSACTIONS
# ============================================================

def get_erc20_transactions(
    wallet_address: str,
    page: int = 1,
    offset: int = MAX_ERC20_TRANSACTIONS
):
    """Fetch ERC20 token transfers separately."""

    wallet_address = normalize_address(wallet_address)

    params = {
        "chainid": "1",
        "module": "account",
        "action": "tokentx",
        "address": wallet_address,
        "startblock": "0",
        "endblock": "99999999",
        "page": str(page),
        "offset": str(offset),
        "sort": "desc"
    }

    return etherscan_request(params)


# ============================================================
# WEI -> ETH
# ============================================================

def wei_to_eth(value):
    """Convert Wei to ETH safely."""

    try:
        return float(value or 0) / 10**18

    except (ValueError, TypeError, OverflowError):
        return 0.0


# ============================================================
# ADDRESS NORMALIZATION
# ============================================================

def normalize_address(address):
    """Normalize Ethereum address."""

    if not address:
        return ""

    return str(address).strip().lower()


# ============================================================
# CHECK WHETHER ADDRESS IS A CONTRACT
# ============================================================

def is_contract_address(address):
    """
    Determine whether an address is a smart contract.

    Uses Etherscan contract ABI endpoint.
    This is mainly used to avoid treating token contracts
    as normal wallet destinations in the wallet graph.
    """

    address = normalize_address(address)

    if not address:
        return False

    try:

        params = {
            "chainid": "1",
            "module": "contract",
            "action": "getabi",
            "address": address
        }

        request_params = dict(params)
        request_params["apikey"] = ETHERSCAN_API_KEY

        response = requests.get(
            ETHERSCAN_URL,
            params=request_params,
            timeout=10
        )

        if response.status_code != 200:
            return False

        data = response.json()

        result = data.get("result")

        if result and result != "Contract source code not verified":
            return True

    except Exception:
        pass

    return False


# ============================================================
# VALID ETHEREUM ADDRESS
# ============================================================

def is_valid_address(address):
    """Basic Ethereum address validation."""

    address = normalize_address(address)

    return (
        address.startswith("0x")
        and len(address) == 42
    )


# ============================================================
# WALLET GRAPH TRACING
# ============================================================

def trace_wallet(
    wallet_address: str,
    max_hops: int = 3,
    max_wallets_per_hop: int = MAX_WALLETS_PER_HOP,
    max_transactions_per_wallet: int = MAX_TRANSACTIONS_PER_WALLET
):
    """
    Trace native ETH wallet-to-wallet transactions.

    - Supports BOTH incoming and outgoing transactions.
    - Graph edges always keep the real blockchain direction:
          sender -> receiver
    - For outgoing transactions:
          next wallet = transaction receiver
    - For incoming transactions:
          next wallet = transaction sender
    - Smart contracts are ignored.
    - Zero-value transactions are ignored.
    - Maximum tracing depth is 3 hops.
    """

    wallet_address = normalize_address(wallet_address)

    if not is_valid_address(wallet_address):
        raise ValueError(
            "Invalid Ethereum wallet address."
        )

    if max_hops < 1 or max_hops > 3:
        raise ValueError(
            "max_hops must be between 1 and 3."
        )

    # ========================================================
    # GRAPH STORAGE
    # ========================================================

    nodes = {}

    edges = []

    edge_keys = set()

    queried_wallets = set()

    discovered_wallets = set()

    # ========================================================
    # CONTRACT CACHE
    # ========================================================

    contract_cache = {}

    # ========================================================
    # ROOT WALLET
    # ========================================================

    nodes[wallet_address] = {
        "id": wallet_address,
        "address": wallet_address,
        "hop": 0
    }

    discovered_wallets.add(wallet_address)

    current_frontier = [wallet_address]

    print(
        f"[TRACE] Starting trace for {wallet_address}"
    )

    print(
        f"[TRACE] Maximum hops: {max_hops}"
    )

    # ========================================================
    # HOP LOOP
    # ========================================================

    for hop in range(1, max_hops + 1):

        if not current_frontier:
            break

        print(
            f"\n[TRACE] ===== STARTING HOP {hop} ====="
        )

        next_frontier = []

        candidate_wallets = {}

        # ====================================================
        # PROCESS CURRENT FRONTIER
        # ====================================================

        for wallet_index, current_wallet in enumerate(
            current_frontier,
            start=1
        ):

            current_wallet = normalize_address(
                current_wallet
            )

            if current_wallet in queried_wallets:
                continue

            queried_wallets.add(current_wallet)

            print(
                f"[TRACE] Hop {hop} "
                f"Wallet {wallet_index}/"
                f"{len(current_frontier)}"
            )

            print(
                f"[TRACE] Fetching: {current_wallet}"
            )

            # =================================================
            # FETCH TRANSACTIONS
            # =================================================

            try:

                transactions = get_eth_transactions(
                    current_wallet,
                    page=1,
                    offset=max_transactions_per_wallet
                )

            except Exception as e:

                print(
                    f"[TRACE] Failed: {current_wallet}"
                )

                print(str(e))

                continue

            print(
                f"[TRACE] Transactions received: "
                f"{len(transactions)}"
            )

            time.sleep(REQUEST_DELAY)

            # =================================================
            # PROCESS TRANSACTIONS
            # =================================================

            for tx in transactions:

                if not isinstance(tx, dict):
                    continue

                tx_from = normalize_address(
                    tx.get("from")
                )

                tx_to = normalize_address(
                    tx.get("to")
                )

                # ---------------------------------------------
                # Ignore malformed transactions
                # ---------------------------------------------

                if not tx_from or not tx_to:
                    continue

                # ---------------------------------------------
                # Ignore self-transfers
                # ---------------------------------------------

                if tx_from == tx_to:
                    continue

                # ---------------------------------------------
                # Check whether current wallet is involved
                # ---------------------------------------------

                if (
                    tx_from != current_wallet
                    and
                    tx_to != current_wallet
                ):
                    continue

                # ---------------------------------------------
                # Convert ETH value
                # ---------------------------------------------

                value_eth = wei_to_eth(
                    tx.get("value", 0)
                )

                # ---------------------------------------------
                # Ignore zero-value transactions
                # ---------------------------------------------

                if value_eth <= 0:
                    continue

                transaction_hash = tx.get("hash")

                timestamp = tx.get(
                    "timeStamp"
                )

                # =================================================
                # DETERMINE COUNTERPARTY
                # =================================================
                #
                # OUTGOING:
                # current wallet -> another wallet
                #
                # INCOMING:
                # another wallet -> current wallet
                #
                # This is the important fix.
                # =================================================

                if tx_from == current_wallet:

                    # Outgoing transaction
                    source = tx_from
                    target = tx_to
                    counterparty = tx_to

                else:

                    # Incoming transaction
                    source = tx_from
                    target = tx_to
                    counterparty = tx_from

                # ---------------------------------------------
                # Validate counterparty
                # ---------------------------------------------

                if not is_valid_address(counterparty):
                    continue

                # ---------------------------------------------
                # Root wallet should never be treated as a
                # candidate for another hop.
                # ---------------------------------------------

                if counterparty == wallet_address:
                    pass

                # ---------------------------------------------
                # CONTRACT CHECK
                # ---------------------------------------------

                if counterparty not in contract_cache:

                    try:

                        contract_cache[counterparty] = (
                            is_contract_address(counterparty)
                        )

                    except Exception:

                        contract_cache[counterparty] = False

                if contract_cache[counterparty]:

                    print(
                        f"[TRACE] Ignoring contract: "
                        f"{counterparty}"
                    )

                    continue

                # =================================================
                # UNIQUE EDGE
                # =================================================

                edge_key = (
                    source,
                    target,
                    transaction_hash
                )

                if edge_key in edge_keys:
                    continue

                edge_keys.add(edge_key)

                # =================================================
                # ADD REAL BLOCKCHAIN EDGE
                # =================================================

                edges.append({

                    "source":
                        source,

                    "target":
                        target,

                    "transaction_hash":
                        transaction_hash,

                    "value_eth":
                        value_eth,

                    "timestamp":
                        timestamp
                })

                # =================================================
                # ADD COUNTERPARTY NODE
                # =================================================

                if counterparty not in discovered_wallets:

                    discovered_wallets.add(
                        counterparty
                    )

                    nodes[counterparty] = {

                        "id":
                            counterparty,

                        "address":
                            counterparty,

                        "hop":
                            hop
                    }

                # =================================================
                # CANDIDATE FOR NEXT HOP
                # =================================================

                if (
                    counterparty != wallet_address
                    and
                    counterparty not in queried_wallets
                ):

                    previous_value = candidate_wallets.get(
                        counterparty,
                        0
                    )

                    candidate_wallets[counterparty] = max(
                        previous_value,
                        value_eth
                    )

        # ========================================================
        # SELECT TOP NEXT-HOP WALLETS
        # ========================================================

        sorted_candidates = sorted(
            candidate_wallets.items(),
            key=lambda item: item[1],
            reverse=True
        )

        for wallet, value in sorted_candidates[
            :max_wallets_per_hop
        ]:

            next_frontier.append(wallet)

        # ========================================================
        # DEBUG OUTPUT
        # ========================================================

        print(
            f"[TRACE] Candidates discovered: "
            f"{len(candidate_wallets)}"
        )

        print(
            f"[TRACE] Next hop wallets: "
            f"{len(next_frontier)}"
        )

        print(
            f"[TRACE] Total nodes: "
            f"{len(nodes)}"
        )

        print(
            f"[TRACE] Total edges: "
            f"{len(edges)}"
        )

        current_frontier = next_frontier

        if hop == max_hops:
            break

    # ========================================================
    # TRACE COMPLETE
    # ========================================================

    print(
        "\n[TRACE] ===== TRACE COMPLETE ====="
    )

    print(
        f"[TRACE] Nodes: {len(nodes)}"
    )

    print(
        f"[TRACE] Edges: {len(edges)}"
    )

    print(
        f"[TRACE] Wallets queried: "
        f"{len(queried_wallets)}"
    )

    # ========================================================
    # FINAL RESULT
    # ========================================================

    return {

        "nodes":
            list(nodes.values()),

        "edges":
            edges
    }