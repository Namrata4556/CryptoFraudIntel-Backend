from datetime import datetime


def detect_suspicious_patterns(wallet_address, transactions, traced_wallets):

    wallet_address = wallet_address.lower()

    # --------------------------------------------------
    # FAN-OUT
    # --------------------------------------------------

    outgoing_wallets = set()

    for tx in transactions:

        sender = (tx.get("from") or "").lower()
        receiver = (tx.get("to") or "").lower()

        if sender == wallet_address and receiver:
            outgoing_wallets.add(receiver)

    fan_out_detected = len(outgoing_wallets) >= 3


    # --------------------------------------------------
    # FAN-IN
    # --------------------------------------------------

    incoming_wallets = set()

    for tx in transactions:

        sender = (tx.get("from") or "").lower()
        receiver = (tx.get("to") or "").lower()

        if receiver == wallet_address and sender:
            incoming_wallets.add(sender)

    fan_in_detected = len(incoming_wallets) >= 3


    # --------------------------------------------------
    # RAPID TRANSACTIONS
    # --------------------------------------------------

    timestamps = []

    for tx in transactions:

        timestamp = tx.get("timestamp")

        if timestamp:

            try:

                time_value = datetime.fromisoformat(
                    timestamp
                )

                timestamps.append(time_value)

            except Exception:
                pass

    timestamps.sort()

    rapid_transactions = False

    for i in range(1, len(timestamps)):

        difference = (
            timestamps[i] - timestamps[i - 1]
        ).total_seconds()

        if difference <= 60:

            rapid_transactions = True
            break


    # --------------------------------------------------
    # MULTI-HOP / LAYERING INDICATOR
    # --------------------------------------------------

    max_hop = 0

    for wallet in traced_wallets:

        hop = wallet.get("hop", 0)

        if hop > max_hop:
            max_hop = hop

    multi_hop_detected = max_hop >= 2


    # --------------------------------------------------
    # SUSPICIOUS PATTERNS LIST
    # --------------------------------------------------

    patterns = []

    if fan_out_detected:

        patterns.append({
            "pattern": "Fan-out",
            "description": "Wallet sends funds to multiple wallets",
            "severity": "medium",
            "counterparties": len(outgoing_wallets)
        })

    if fan_in_detected:

        patterns.append({
            "pattern": "Fan-in",
            "description": "Wallet receives funds from multiple wallets",
            "severity": "medium",
            "counterparties": len(incoming_wallets)
        })

    if rapid_transactions:

        patterns.append({
            "pattern": "Rapid Transactions",
            "description": "Multiple transactions occurred within a short time period",
            "severity": "medium"
        })

    if multi_hop_detected:

        patterns.append({
            "pattern": "Multi-hop Movement",
            "description": "Funds can be traced through multiple wallet hops",
            "severity": "high",
            "maximum_hop": max_hop
        })


    # --------------------------------------------------
    # RETURN RESULT
    # --------------------------------------------------

    return {
        "suspicious_pattern_count": len(patterns),

        "patterns": patterns,

        "indicators": {
            "fan_out": fan_out_detected,
            "fan_in": fan_in_detected,
            "rapid_transactions": rapid_transactions,
            "multi_hop_movement": multi_hop_detected
        }
    }