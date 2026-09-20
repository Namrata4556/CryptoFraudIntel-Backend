from blockchain.adapters import BlockchainAdapter
from services.ethereum_service import (
    get_eth_transactions,
    trace_wallet,
)


class EthereumAdapter(BlockchainAdapter):

    def get_transactions(self, wallet_address):
        return get_eth_transactions(wallet_address)

    def trace(self, wallet_address, max_hops=3):
        return trace_wallet(
            wallet_address,
            max_hops=max_hops
        )