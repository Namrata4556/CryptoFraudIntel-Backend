from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from blockchain.manager import BlockchainManager

from services.exchange_service import (
    identify_exchange_interactions,
    identify_exchanges_from_graph,
)

from feature_engineering import build_wallet_features
from ml.fraud_model import predict_fraud
from ml.xgboost_model import predict_xgboost

from services.exchange_service import (
    identify_exchange_interactions,
    identify_exchanges_from_graph,
)

from feature_engineering import build_wallet_features
from ml.fraud_model import predict_fraud
from ml.xgboost_model import predict_xgboost


app = FastAPI(
    title="Crypto Fraud Intelligence System",
    description="Real-time cryptocurrency wallet fraud analysis",
    version="1.0.0",
)

blockchain_manager = BlockchainManager()

# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():
    return {
        "message": "Crypto Fraud Intelligence System API",
        "status": "running",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "healthy",
    }


# ============================================================
# COMBINED RISK
# ============================================================

def calculate_combined_risk(
    rf_prediction,
    xgb_prediction,
):
    probabilities = []

    if isinstance(rf_prediction, dict):
        rf_probability = rf_prediction.get("fraud_probability")

        if rf_probability is not None:
            probabilities.append(float(rf_probability))

    if isinstance(xgb_prediction, dict):
        xgb_probability = xgb_prediction.get("fraud_probability")

        if xgb_probability is not None:
            probabilities.append(float(xgb_probability))

    if not probabilities:
        return {
            "combined_fraud_probability": 0,
            "combined_fraud_percentage": 0,
            "combined_risk_level": "LOW",
            "models_used": 0,
        }

    combined_probability = sum(probabilities) / len(probabilities)

    if combined_probability >= 0.80:
        risk_level = "CRITICAL"

    elif combined_probability >= 0.60:
        risk_level = "HIGH"

    elif combined_probability >= 0.30:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    return {
        "combined_fraud_probability": combined_probability,
        "combined_fraud_percentage": round(
            combined_probability * 100,
            2,
        ),
        "combined_risk_level": risk_level,
        "models_used": len(probabilities),
    }


# ============================================================
# ANALYZE WALLET
# ============================================================

@app.post("/analyze-wallet")
def analyze_wallet(
    wallet_address: str,
    blockchain: str = "ethereum"
):

    # --------------------------------------------------------
    # Basic validation
    # --------------------------------------------------------

    if not wallet_address or not wallet_address.strip():
        raise HTTPException(
            status_code=400,
            detail="Wallet address is required.",
        )

    wallet_address = wallet_address.strip()

    print("\n")
    print("=" * 60)
    print("CRYPTO FRAUD INTELLIGENCE SYSTEM")
    print("=" * 60)
    print(f"Wallet: {wallet_address}")
    print("=" * 60)

    # ========================================================
    # 1. FETCH TRANSACTIONS
    # ========================================================

    try:

        transactions = blockchain_manager.get_transactions(
            blockchain,
            wallet_address
        )
    except Exception as e:

        print("ERROR FETCHING TRANSACTIONS:")
        print(e)

        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch {blockchain} transactions: {str(e)}",
        )

    if transactions is None:
        transactions = []

    print(
        f"Transactions fetched: {len(transactions)}"
    )

        # ========================================================
    # 2. PREPARE TRANSACTIONS FOR ML
    # ========================================================

    prepared_transactions = []

    for tx in transactions:

        if not isinstance(tx, dict):
            continue

        # ----------------------------------------------------
        # BITCOIN
        # ----------------------------------------------------

        if blockchain.lower() == "bitcoin":

            value_btc = tx.get("value_btc", 0)

            try:
                value_btc = float(value_btc or 0)
            except (TypeError, ValueError):
                value_btc = 0.0

            prepared_tx = {
                "wallet_address": wallet_address,

                "hash": tx.get("hash"),

                "from": tx.get("from"),

                "to": tx.get("to"),

                # Keep BTC value for Bitcoin
                "value": value_btc,

                "value_btc": value_btc,

                # Feature engineering expects value_eth.
                # For Bitcoin this field represents the
                # normalized native-coin value, not actual ETH.
                "value_eth": value_btc,

                "timestamp": tx.get("timestamp"),

                "timeStamp": tx.get("timestamp"),

                "fee": tx.get("fee", 0),

                "block_number": tx.get(
                    "block_number"
                ),

                "blockchain": "bitcoin",

                "sent_value_satoshi": tx.get(
                    "sent_value_satoshi",
                    0
                ),

                "received_value_satoshi": tx.get(
                    "received_value_satoshi",
                    0
                ),

                "senders": tx.get(
                    "senders",
                    []
                ),

                "receivers": tx.get(
                    "receivers",
                    []
                ),
            }

        # ----------------------------------------------------
        # ETHEREUM
        # ----------------------------------------------------

        else:

            raw_value = tx.get("value", 0)

            try:
                value_wei = int(raw_value or 0)
            except (TypeError, ValueError):
                value_wei = 0

            value_eth = value_wei / 10**18

            prepared_tx = {
                "wallet_address": wallet_address,

                "hash": tx.get("hash"),

                "from": tx.get("from"),

                "to": tx.get("to"),

                "value": value_wei,

                "value_eth": value_eth,

                "timestamp": tx.get(
                    "timeStamp",
                    tx.get("timestamp")
                ),

                "timeStamp": tx.get(
                    "timeStamp",
                    tx.get("timestamp")
                ),

                "gas": tx.get("gas"),

                "gasPrice": tx.get("gasPrice"),

                "isError": tx.get("isError"),

                "input": tx.get("input"),

                "contractAddress": tx.get(
                    "contractAddress"
                ),

                "functionName": tx.get(
                    "functionName"
                ),

                "blockchain": "ethereum",
            }

        prepared_transactions.append(
            prepared_tx
        )

    print(
        "[3] Prepared transactions:",
        len(prepared_transactions)
    )

    if blockchain.lower() == "bitcoin":

        print(
            "[3] Total BTC values prepared:",
            sum(
                float(
                    tx.get("value_btc", 0) or 0
                )
                for tx in prepared_transactions
            )
        )

    else:

        print(
            "[3] Total ETH values prepared:",
            sum(
                float(
                    tx.get("value_eth", 0) or 0
                )
                for tx in prepared_transactions
            )
        )

    # ========================================================
    # 3. BUILD ML FEATURES
    # ========================================================

    try:

        features = build_wallet_features(
            prepared_transactions
        )

    except Exception as e:

        print("ERROR BUILDING FEATURES:")
        print(e)

        raise HTTPException(
            status_code=500,
            detail=f"Feature engineering failed: {str(e)}",
        )
        
    # ========================================================
    # 4. RANDOM FOREST
    # ========================================================

    try:

        rf_prediction = predict_fraud(
            features
        )

    except Exception as e:

        print("RANDOM FOREST ERROR:")
        print(e)

        rf_prediction = {
            "model": "Random Forest",
            "prediction": None,
            "label": "ERROR",
            "fraud_probability": 0,
            "fraud_percentage": 0,
            "risk_level": "UNKNOWN",
            "error": str(e),
        }

    # ========================================================
    # 5. XGBOOST
    # ========================================================

    try:

        xgb_prediction = predict_xgboost(
            features
        )

    except Exception as e:

        print("XGBOOST ERROR:")
        print(e)

        xgb_prediction = {
            "model": "XGBoost",
            "prediction": None,
            "label": "ERROR",
            "fraud_probability": 0,
            "fraud_percentage": 0,
            "risk_level": "UNKNOWN",
            "error": str(e),
        }

    # ========================================================
    # 6. COMBINED RISK
    # ========================================================

    combined_risk = calculate_combined_risk(
        rf_prediction,
        xgb_prediction,
    )

    # ========================================================
    # 7. DIRECT EXCHANGE DETECTION
    # ========================================================

    try:

        direct_exchange_result = (
            identify_exchange_interactions(
                prepared_transactions,
                wallet_address,
            )
        )

    except TypeError:

        # Compatibility fallback if the function
        # only accepts transactions.

        try:

            direct_exchange_result = (
                identify_exchange_interactions(
                    prepared_transactions
                )
            )

        except Exception as e:

            print("DIRECT EXCHANGE DETECTION ERROR:")
            print(e)

            direct_exchange_result = {
                "exchange_found": False,
                "exchanges": [],
                "interactions": [],
                "error": str(e),
            }

    except Exception as e:

        print("DIRECT EXCHANGE DETECTION ERROR:")
        print(e)

        direct_exchange_result = {
            "exchange_found": False,
            "exchanges": [],
            "interactions": [],
            "error": str(e),
        }

    if direct_exchange_result is None:
        direct_exchange_result = {}

    # ========================================================
    # 8. WALLET TRACE / GRAPH
    # ========================================================

    traced_graph = None

    try:

        traced_graph = blockchain_manager.trace_wallet(
            blockchain,
            wallet_address,
            max_hops=3,
            transactions=transactions
        )

    except Exception as e:

        print("WALLET TRACE ERROR:")
        print(e)

        traced_graph = {
            "nodes": [],
            "edges": [],
            "error": str(e),
        }
    # ========================================================
    # 9. EXTRACT GRAPH NODES / EDGES
    # ========================================================

    graph_nodes = []
    graph_edges = []

    if isinstance(traced_graph, dict):

        graph_nodes = (
            traced_graph.get("nodes")
            or traced_graph.get("graph_nodes")
            or []
        )

        graph_edges = (
            traced_graph.get("edges")
            or traced_graph.get("graph_edges")
            or []
        )

    else:

        try:

            graph_nodes = getattr(
                traced_graph,
                "nodes",
                [],
            )

        except Exception:

            graph_nodes = []

        try:

            graph_edges = getattr(
                traced_graph,
                "edges",
                [],
            )

        except Exception:

            graph_edges = []

    if graph_nodes is None:
        graph_nodes = []

    if graph_edges is None:
        graph_edges = []

    print(
        f"Graph nodes: {len(graph_nodes)}"
    )

    print(
        f"Graph edges: {len(graph_edges)}"
    )

    # ========================================================
    # 10. INDIRECT EXCHANGE DETECTION
    # ========================================================

    try:

        indirect_exchange_result = (
            identify_exchanges_from_graph(
                traced_graph
            )
        )

    except Exception as e:

        print("INDIRECT EXCHANGE DETECTION ERROR:")
        print(e)

        indirect_exchange_result = []

    if indirect_exchange_result is None:
        indirect_exchange_result = []

    # ========================================================
    # 11. NORMALIZE DIRECT EXCHANGES
    # ========================================================

    direct_matches = []

    if isinstance(
        direct_exchange_result,
        dict,
    ):

        direct_matches = (
            direct_exchange_result.get(
                "exchanges"
            )
            or direct_exchange_result.get(
                "identified_exchanges"
            )
            or direct_exchange_result.get(
                "matches"
            )
            or []
        )

    elif isinstance(
        direct_exchange_result,
        list,
    ):

        direct_matches = (
            direct_exchange_result
        )

    if direct_matches is None:
        direct_matches = []

    # ========================================================
    # 12. NORMALIZE INDIRECT EXCHANGES
    # ========================================================

    indirect_matches = []

    if isinstance(
        indirect_exchange_result,
        dict,
    ):

        indirect_matches = (
            indirect_exchange_result.get(
                "exchanges"
            )
            or indirect_exchange_result.get(
                "identified_exchanges"
            )
            or indirect_exchange_result.get(
                "matches"
            )
            or []
        )

    elif isinstance(
        indirect_exchange_result,
        list,
    ):

        indirect_matches = (
            indirect_exchange_result
        )

    if indirect_matches is None:
        indirect_matches = []

    # ========================================================
    # 13. MERGE EXCHANGES
    # ========================================================

    all_exchanges = []

    all_exchanges.extend(
        direct_matches
    )

    all_exchanges.extend(
        indirect_matches
    )

    # ========================================================
    # 14. DEDUPLICATE EXCHANGES
    # ========================================================

    unique_exchanges = []

    seen_exchange_names = set()

    for exchange in all_exchanges:

        if isinstance(exchange, str):

            exchange_name = exchange

        elif isinstance(exchange, dict):

            exchange_name = (
                exchange.get("name")
                or exchange.get("exchange")
                or exchange.get("label")
                or str(exchange)
            )

        else:

            exchange_name = str(exchange)

        exchange_key = (
            str(exchange_name)
            .strip()
            .lower()
        )

        if exchange_key not in seen_exchange_names:

            seen_exchange_names.add(
                exchange_key
            )

            unique_exchanges.append(
                exchange
            )

    # ========================================================
    # 15. EXCHANGE FOUND
    # ========================================================

    exchange_found = (
        len(unique_exchanges) > 0
    )

    # ========================================================
    # 16. TRANSACTION SUMMARY
    # ========================================================

    sent_count = 0
    received_count = 0

    total_value_sent = 0.0
    total_value_received = 0.0

    wallet_lower = wallet_address.lower()

    for tx in prepared_transactions:

        from_address = str(
            tx.get("from") or ""
        ).lower()

        to_address = str(
            tx.get("to") or ""
        ).lower()

        if blockchain.lower() == "bitcoin":

            value = float(
                tx.get("value_btc", 0) or 0
            )

        else:

            value = float(
                tx.get("value_eth", 0) or 0
            )

        if from_address == wallet_lower:

            sent_count += 1
            total_value_sent += value

        if to_address == wallet_lower:

            received_count += 1
            total_value_received += value

    total_value_balance = (
        total_value_received
        - total_value_sent
    )

    transaction_summary = {

        "blockchain": blockchain.lower(),

        "sent_transactions": sent_count,

        "received_transactions": received_count,

        "total_sent": total_value_sent,

        "total_received": total_value_received,

        "total_balance": total_value_balance,

        # Frontend compatibility
        "total_eth_sent": (
            total_value_sent
            if blockchain.lower() == "ethereum"
            else 0.0
        ),

        "total_eth_received": (
            total_value_received
            if blockchain.lower() == "ethereum"
            else 0.0
        ),

        "total_eth_balance": (
            total_value_balance
            if blockchain.lower() == "ethereum"
            else 0.0
        ),

        # Bitcoin-specific fields
        "total_btc_sent": (
            total_value_sent
            if blockchain.lower() == "bitcoin"
            else 0.0
        ),

        "total_btc_received": (
            total_value_received
            if blockchain.lower() == "bitcoin"
            else 0.0
        ),

        "total_btc_balance": (
            total_value_balance
            if blockchain.lower() == "bitcoin"
            else 0.0
        ),
    }

    # ========================================================
    # 17. EXCHANGE ANALYSIS
    # ========================================================

    exchange_analysis = {

        "exchange_found": exchange_found,

        "exchange_count": len(
            unique_exchanges
        ),

        "message": (
            "Exchange interaction detected"
            if exchange_found
            else "No known exchange interaction detected"
        ),

        # Frontend-friendly
        "identified_exchanges":
            unique_exchanges,

        "exchanges":
            unique_exchanges,

        # Direct analysis
        "direct_analysis":
            direct_exchange_result,

        # Direct matches
        "direct_matches":
            direct_matches,

        # Indirect matches
        "indirect_matches":
            indirect_matches,

        # Graph analysis
        "graph_analysis":
            indirect_matches,

        # Graph information
        "graph_nodes":
            graph_nodes,

        "graph_edges":
            graph_edges,

        # Raw interactions
        "interactions":
            (
                direct_exchange_result.get(
                    "interactions",
                    []
                )
                if isinstance(
                    direct_exchange_result,
                    dict,
                )
                else []
            ),
    }

    # ========================================================
    # 18. FINAL RESULT
    # ========================================================

    result = {

        # ----------------------------------------------------
        # Wallet
        # ----------------------------------------------------

        "wallet_address":
            wallet_address,

        # ----------------------------------------------------
        # Transactions
        # ----------------------------------------------------
        "blockchain": 
            blockchain.lower(),

        "transaction_count":
            len(prepared_transactions),

        "transactions":
            prepared_transactions,

        "transaction_summary":
            transaction_summary,

        # ----------------------------------------------------
        # Machine Learning
        # ----------------------------------------------------

        "ml_prediction":
            rf_prediction,

        "xgboost_prediction":
            xgb_prediction,

        "model_comparison":
            combined_risk,

        # ----------------------------------------------------
        # Exchange analysis
        # ----------------------------------------------------

        "exchange_analysis":
            exchange_analysis,

        # ----------------------------------------------------
        # Graph
        # ----------------------------------------------------

        "wallet_graph":
            traced_graph,

        "graph_nodes":
            graph_nodes,

        "graph_edges":
            graph_edges,

        # ----------------------------------------------------
        # Useful frontend fields
        # ----------------------------------------------------

        "transactions_analyzed":
            len(prepared_transactions),

        "risk_level":
            combined_risk[
                "combined_risk_level"
            ],

        "fraud_probability":
            combined_risk[
                "combined_fraud_probability"
            ],

        "fraud_percentage":
            combined_risk[
                "combined_fraud_percentage"
            ],
    }

    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print("\n")
    print("-" * 50)
    print("TRANSACTION SUMMARY")
    print("-" * 50)

    print(
        f"Blockchain: {blockchain.lower()}"
    )

    print(
        f"Sent transactions: {sent_count}"
    )

    print(
        f"Received transactions: {received_count}"
    )

    print(
        f"Total {blockchain.upper()} sent: "
        f"{total_value_sent}"
    )

    print(
        f"Total {blockchain.upper()} received: "
        f"{total_value_received}"
    )

    print(
        f"Total {blockchain.upper()} balance: "
        f"{total_value_balance}"
    )

    print("\n")
    print("=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)

    print(
        f"Wallet: {wallet_address}"
    )

    print(
        f"Transactions: {len(prepared_transactions)}"
    )

    print(
        f"Exchange found: {exchange_found}"
    )

    print(
        f"Distinct exchanges: {len(unique_exchanges)}"
    )

    print(
        f"Random Forest: {rf_prediction}"
    )

    print(
        f"XGBoost: {xgb_prediction}"
    )

    print(
        f"Combined Risk: {combined_risk}"
    )

    print(
        f"Graph nodes: {len(graph_nodes)}"
    )

    print(
        f"Graph edges: {len(graph_edges)}"
    )

    print("=" * 60)
    print()

    return result