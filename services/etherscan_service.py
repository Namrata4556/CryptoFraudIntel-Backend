import os
import requests
from dotenv import load_dotenv

load_dotenv()

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY")

ETHERSCAN_URL = "https://api.etherscan.io/v2/api"


def get_transactions(wallet_address: str):

    params = {
        "chainid": "1",
        "module": "account",
        "action": "txlist",
        "address": wallet_address,
        "startblock": 0,
        "endblock": 999999999,
        "page": 1,
        "offset": 20,
        "sort": "desc",
        "apikey": ETHERSCAN_API_KEY
    }

    response = requests.get(
        ETHERSCAN_URL,
        params=params,
        timeout=15
    )

    response.raise_for_status()

    return response.json()