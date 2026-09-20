from blockchain.adapters import BlockchainAdapter

from services.bitcoin_service import (
    get_btc_transactions,
    trace_btc_wallet,
    normalize_btc_transaction,
)


class BitcoinAdapter(BlockchainAdapter):

    def __init__(self):
        self.last_raw_transactions = []

    def get_transactions(self, wallet_address):

        raw_transactions = get_btc_transactions(
            wallet_address
        )

        # Save RAW transactions so trace()
        # can reuse them without another API call.
        self.last_raw_transactions = raw_transactions

        return [
            normalize_btc_transaction(
                tx,
                wallet_address
            )
            for tx in raw_transactions
        ]

    def trace(
        self,
        wallet_address,
        max_hops=3,
        transactions=None
    ):

        # Bitcoin graph tracing requires RAW transactions
        # containing "inputs" and "out".

        if self.last_raw_transactions:

            raw_transactions = self.last_raw_transactions

        elif transactions:

            first_tx = transactions[0]

            if (
                isinstance(first_tx, dict)
                and "inputs" in first_tx
                and "out" in first_tx
            ):
                raw_transactions = transactions

            else:
                raw_transactions = get_btc_transactions(
                    wallet_address
                )

        else:

            raw_transactions = get_btc_transactions(
                wallet_address
            )

        return trace_btc_wallet(
            wallet_address,
            raw_transactions,
            max_hops=max_hops
        )