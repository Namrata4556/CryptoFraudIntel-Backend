class BlockchainAdapter:

    def get_transactions(self, wallet_address):
        raise NotImplementedError

    def trace(self, wallet_address, max_hops=3):
        raise NotImplementedError