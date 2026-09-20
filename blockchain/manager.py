from blockchain.adapters.ethereum import EthereumAdapter
from blockchain.adapters.bitcoin import BitcoinAdapter


class BlockchainManager:

    def __init__(self):

        self.adapters = {
            "ethereum": EthereumAdapter(),
            "bitcoin": BitcoinAdapter()
        }

    def get_adapter(self, blockchain):

        blockchain = blockchain.lower()

        if blockchain not in self.adapters:

            raise ValueError(
                f"Unsupported blockchain: {blockchain}"
            )

        return self.adapters[blockchain]

    def get_transactions(
        self,
        blockchain,
        wallet_address
    ):

        adapter = self.get_adapter(
            blockchain
        )

        return adapter.get_transactions(
            wallet_address
        )

    def trace_wallet(
        self,
        blockchain,
        wallet_address,
        max_hops=3,
        transactions=None
    ):

        adapter = self.get_adapter(
            blockchain
        )

        if blockchain.lower() == "bitcoin":

            return adapter.trace(
                wallet_address,
                max_hops=max_hops,
                transactions=transactions
            )

        return adapter.trace(
            wallet_address,
            max_hops=max_hops
        )