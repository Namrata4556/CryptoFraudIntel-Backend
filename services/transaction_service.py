from datetime import datetime


def format_transactions(raw_data):

    transactions = raw_data.get("result", [])

    formatted_transactions = []

    for tx in transactions:

        value_wei = int(tx.get("value", 0))

        # Convert Wei → ETH
        value_eth = value_wei / 10**18

        timestamp = int(tx.get("timeStamp", 0))

        if timestamp:
            readable_time = datetime.fromtimestamp(timestamp).isoformat()
        else:
            readable_time = None

        formatted_transactions.append({
            "hash": tx.get("hash"),
            "from": tx.get("from"),
            "to": tx.get("to"),
            "amount_eth": value_eth,
            "timestamp": readable_time,
            "block_number": tx.get("blockNumber"),
            "status": tx.get("txreceipt_status")
        })

    return formatted_transactions