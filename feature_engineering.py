# ============================================================
# FEATURE ENGINEERING
# Crypto Fraud Intelligence System
# ============================================================

import pandas as pd


# ============================================================
# EXACT FEATURES EXPECTED BY fraud_model.pkl
# DO NOT CHANGE SPELLING, SPACES, OR CAPITALIZATION
# ============================================================

MODEL_FEATURES = [
    "Avg min between sent tnx",
    "Avg min between received tnx",
    "Time Diff between first and last (Mins)",
    "Sent tnx",
    "Received Tnx",
    "Number of Created Contracts",
    "Unique Received From Addresses",
    "Unique Sent To Addresses",
    "min value received",
    "max value received ",
    "avg val received",
    "min val sent",
    "max val sent",
    "avg val sent",
    "min value sent to contract",
    "max val sent to contract",
    "avg value sent to contract",
    "total transactions (including tnx to create contract",
    "total Ether sent",
    "total ether received",
    "total ether sent contracts",
    "total ether balance",
    " Total ERC20 tnxs",
    " ERC20 total Ether received",
    " ERC20 total ether sent",
    " ERC20 total Ether sent contract",
    " ERC20 uniq sent addr",
    " ERC20 uniq rec addr",
    " ERC20 uniq sent addr.1",
    " ERC20 uniq rec contract addr",
    " ERC20 avg time between sent tnx",
    " ERC20 avg time between rec tnx",
    " ERC20 avg time between rec 2 tnx",
    " ERC20 avg time between contract tnx",
    " ERC20 min val rec",
    " ERC20 max val rec",
    " ERC20 avg val rec",
    " ERC20 min val sent",
    " ERC20 max val sent",
    " ERC20 avg val sent",
    " ERC20 min val sent contract",
    " ERC20 max val sent contract",
    " ERC20 avg val sent contract",
    " ERC20 uniq sent token name",
    " ERC20 uniq rec token name",
    " ERC20_most_rec_token_type",
]


# ============================================================
# SAFE FLOAT
# ============================================================

def safe_float(value, default=0.0):
    """
    Safely convert any value to float.
    Invalid / missing values become default.
    """

    try:

        if value is None:
            return default

        number = float(value)

        if pd.isna(number):
            return default

        return number

    except (ValueError, TypeError):
        return default


# ============================================================
# SAFE SERIES STATISTICS
# ============================================================

def safe_min(series):

    if series is None or len(series) == 0:
        return 0.0

    return safe_float(series.min())


def safe_max(series):

    if series is None or len(series) == 0:
        return 0.0

    return safe_float(series.max())


def safe_mean(series):

    if series is None or len(series) == 0:
        return 0.0

    return safe_float(series.mean())


# ============================================================
# BUILD WALLET FEATURES
# ============================================================

def build_wallet_features(transactions):
    """
    Convert normalized blockchain transactions into
exactly 46 features expected by fraud_model.pkl.

Ethereum transactions use ETH values.
Bitcoin transactions use BTC values mapped into
the common value feature fields.

Note:
The fraud model was trained on Ethereum transaction
features, so Bitcoin predictions are experimental and
should not be interpreted as a Bitcoin-trained model result..

    Current data source:
        Normal Ethereum transactions.

    ERC20-specific features are currently zero because
    ERC20 transaction fetching is handled separately later.
    """

    # ========================================================
    # EMPTY TRANSACTION CHECK
    # ========================================================

    if not transactions:

        features = {}

        for feature in MODEL_FEATURES:

            if feature == "ERC20_most_rec_token_type":
                features[feature] = ""

            else:
                features[feature] = 0.0

        return features


    # ========================================================
    # CREATE DATAFRAME
    # ========================================================

    df = pd.DataFrame(transactions)


    # ========================================================
    # MAKE SURE REQUIRED COLUMNS EXIST
    # ========================================================

    required_columns = [
        "from",
        "to",
        "value",
        "timeStamp"
    ]

    for column in required_columns:

        if column not in df.columns:
            df[column] = ""


    # ========================================================
    # NORMALIZE ADDRESSES
    # ========================================================

    df["from"] = (
        df["from"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )

    df["to"] = (
        df["to"]
        .fillna("")
        .astype(str)
        .str.strip()
        .str.lower()
    )


    # ========================================================
    # WALLET ADDRESS
    # ========================================================

    wallet = ""

    if "wallet_address" in df.columns:

        wallet_values = (
            df["wallet_address"]
            .dropna()
            .astype(str)
        )

        if len(wallet_values) > 0:

            wallet = (
                wallet_values.iloc[0]
                .strip()
                .lower()
            )


    # If wallet_address wasn't supplied,
    # infer it from the transaction data.

    if not wallet:

        if len(df) > 0:

            first_from = str(
                df.iloc[0]["from"]
            ).strip().lower()

            first_to = str(
                df.iloc[0]["to"]
            ).strip().lower()

            if first_from.startswith("0x"):
                wallet = first_from

            elif first_to.startswith("0x"):
                wallet = first_to


    # ========================================================
    # VALUE CONVERSION
    # ========================================================

    if "value_eth" not in df.columns:

        df["value_eth"] = (
            pd.to_numeric(
                df["value"],
                errors="coerce"
            )
            .fillna(0.0)
            / 10**18
        )

    else:

        df["value_eth"] = (
            pd.to_numeric(
                df["value_eth"],
                errors="coerce"
            )
            .fillna(0.0)
        )


    # ========================================================
    # TIMESTAMP CONVERSION
    # ========================================================

    if "timestamp" not in df.columns:

        df["timestamp"] = (
            pd.to_numeric(
                df["timeStamp"],
                errors="coerce"
            )
            .fillna(0)
        )

    else:

        df["timestamp"] = (
            pd.to_numeric(
                df["timestamp"],
                errors="coerce"
            )
            .fillna(0)
        )


    # ========================================================
    # SENT / RECEIVED TRANSACTIONS
    # ========================================================

    outgoing = df[
        df["from"] == wallet
    ].copy()

    incoming = df[
        df["to"] == wallet
    ].copy()


    # ========================================================
    # TRANSACTION COUNTS
    # ========================================================

    sent_count = len(outgoing)

    received_count = len(incoming)


    # ========================================================
    # SENT / RECEIVED VALUES
    # ========================================================

    sent_values = (
        outgoing["value_eth"]
        if len(outgoing) > 0
        else pd.Series(dtype=float)
    )

    received_values = (
        incoming["value_eth"]
        if len(incoming) > 0
        else pd.Series(dtype=float)
    )


    # ========================================================
    # UNIQUE ADDRESSES
    # ========================================================

    unique_received = (
        incoming["from"]
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )

    unique_sent = (
        outgoing["to"]
        .replace("", pd.NA)
        .dropna()
        .nunique()
    )


    # ========================================================
    # TIME DIFFERENCE
    # ========================================================

    timestamps = (
        df["timestamp"]
        .replace(0, pd.NA)
        .dropna()
    )

    if len(timestamps) >= 2:

        time_diff_minutes = (
            float(
                timestamps.max()
                - timestamps.min()
            )
            / 60.0
        )

    else:

        time_diff_minutes = 0.0


    # ========================================================
    # SENT TRANSACTION TIME INTERVAL
    # ========================================================

    sent_times = (
        outgoing["timestamp"]
        .replace(0, pd.NA)
        .dropna()
        .sort_values()
    )

    if len(sent_times) >= 2:

        avg_sent_interval = (
            sent_times.diff()
            .dropna()
            .mean()
            / 60.0
        )

    else:

        avg_sent_interval = 0.0


    # ========================================================
    # RECEIVED TRANSACTION TIME INTERVAL
    # ========================================================

    received_times = (
        incoming["timestamp"]
        .replace(0, pd.NA)
        .dropna()
        .sort_values()
    )

    if len(received_times) >= 2:

        avg_received_interval = (
            received_times.diff()
            .dropna()
            .mean()
            / 60.0
        )

    else:

        avg_received_interval = 0.0


    # ========================================================
    # TOTALS
    # ========================================================

    total_sent = safe_float(
        sent_values.sum()
    )

    total_received = safe_float(
        received_values.sum()
    )


    # ========================================================
    # CONTRACT TRANSACTIONS
    # ========================================================

    if "contractAddress" in df.columns:

        contract_transactions = df[
            df["contractAddress"]
            .fillna("")
            .astype(str)
            .str.strip()
            != ""
        ].copy()

    else:

        contract_transactions = df.iloc[0:0].copy()


    # ========================================================
    # CONTRACTS CREATED / USED BY WALLET
    # ========================================================

    sent_contracts = contract_transactions[
        contract_transactions["from"] == wallet
    ]

    sent_contract_values = (
        sent_contracts["value_eth"]
        if len(sent_contracts) > 0
        else pd.Series(dtype=float)
    )


    # ========================================================
    # CONTRACT TIME
    # ========================================================

    contract_timestamps = (
        sent_contracts["timestamp"]
        .replace(0, pd.NA)
        .dropna()
        .sort_values()
    )

    if len(contract_timestamps) >= 2:

        avg_contract_interval = (
            contract_timestamps.diff()
            .dropna()
            .mean()
            / 60.0
        )

    else:

        avg_contract_interval = 0.0


    # ========================================================
    # BUILD NORMAL ETH FEATURES
    # ========================================================

    features = {

        # ----------------------------------------------------
        # Transaction timing
        # ----------------------------------------------------

        "Avg min between sent tnx":
            safe_float(avg_sent_interval),

        "Avg min between received tnx":
            safe_float(avg_received_interval),

        "Time Diff between first and last (Mins)":
            safe_float(time_diff_minutes),


        # ----------------------------------------------------
        # Transaction counts
        # ----------------------------------------------------

        "Sent tnx":
            float(sent_count),

        "Received Tnx":
            float(received_count),

        "Number of Created Contracts":
            float(len(sent_contracts)),


        # ----------------------------------------------------
        # Unique addresses
        # ----------------------------------------------------

        "Unique Received From Addresses":
            float(unique_received),

        "Unique Sent To Addresses":
            float(unique_sent),


        # ----------------------------------------------------
        # Received value statistics
        # ----------------------------------------------------

        "min value received":
            safe_min(received_values),

        "max value received ":
            safe_max(received_values),

        "avg val received":
            safe_mean(received_values),


        # ----------------------------------------------------
        # Sent value statistics
        # ----------------------------------------------------

        "min val sent":
            safe_min(sent_values),

        "max val sent":
            safe_max(sent_values),

        "avg val sent":
            safe_mean(sent_values),


        # ----------------------------------------------------
        # Contract value statistics
        # ----------------------------------------------------

        "min value sent to contract":
            safe_min(sent_contract_values),

        "max val sent to contract":
            safe_max(sent_contract_values),

        "avg value sent to contract":
            safe_mean(sent_contract_values),


        # ----------------------------------------------------
        # Overall transaction statistics
        # ----------------------------------------------------

        "total transactions (including tnx to create contract":
            float(len(df)),

        "total Ether sent":
            total_sent,

        "total ether received":
            total_received,

        "total ether sent contracts":
            safe_float(
                sent_contract_values.sum()
            ),

        # IMPORTANT:
        # Exact model spelling:
        # "total ether balance"
        #
        # NOT:
        # "total Ether balance"

        "total ether balance":
            total_received - total_sent,


        # ====================================================
        # ERC20 FEATURES
        # ====================================================
        #
        # ERC20 transaction fetching will be added later.
        # Keep all 21 ERC20 features so the model always
        # receives exactly 46 features.
        # ====================================================

        " Total ERC20 tnxs":
            0.0,

        " ERC20 total Ether received":
            0.0,

        " ERC20 total ether sent":
            0.0,

        " ERC20 total Ether sent contract":
            0.0,

        " ERC20 uniq sent addr":
            0.0,

        " ERC20 uniq rec addr":
            0.0,

        " ERC20 uniq sent addr.1":
            0.0,

        " ERC20 uniq rec contract addr":
            0.0,

        " ERC20 avg time between sent tnx":
            0.0,

        " ERC20 avg time between rec tnx":
            0.0,

        " ERC20 avg time between rec 2 tnx":
            0.0,

        " ERC20 avg time between contract tnx":
            0.0,

        " ERC20 min val rec":
            0.0,

        " ERC20 max val rec":
            0.0,

        " ERC20 avg val rec":
            0.0,

        " ERC20 min val sent":
            0.0,

        " ERC20 max val sent":
            0.0,

        " ERC20 avg val sent":
            0.0,

        " ERC20 min val sent contract":
            0.0,

        " ERC20 max val sent contract":
            0.0,

        " ERC20 avg val sent contract":
            0.0,

        " ERC20 uniq sent token name":
            0.0,

        " ERC20 uniq rec token name":
            0.0,

        # This is a categorical/string feature.
        "ERC20_most_rec_token_type":
            ""
    }


    # ========================================================
    # FORCE EXACT MODEL FEATURE ORDER
    # ========================================================

    final_features = {}

    for feature in MODEL_FEATURES:

        if feature in features:

            final_features[feature] = features[feature]

        else:

            if feature == "ERC20_most_rec_token_type":

                final_features[feature] = ""

            else:

                final_features[feature] = 0.0


    # ========================================================
    # CLEAN VALUES
    # ========================================================

    for feature in MODEL_FEATURES:

        if feature == "ERC20_most_rec_token_type":

            if final_features[feature] is None:

                final_features[feature] = ""

            else:

                final_features[feature] = str(
                    final_features[feature]
                )

        else:

            final_features[feature] = safe_float(
                final_features[feature]
            )


    # ========================================================
    # FINAL VALIDATION
    # ========================================================

    if len(final_features) != 46:

        raise RuntimeError(
            f"Feature engineering produced "
            f"{len(final_features)} features. "
            f"Expected exactly 46."
        )


    missing_features = [
        feature
        for feature in MODEL_FEATURES
        if feature not in final_features
    ]

    if missing_features:

        raise RuntimeError(
            "Missing model features:\n"
            + "\n".join(missing_features)
        )


    # ========================================================
    # DEBUG INFORMATION
    # ========================================================

    print("\n----------------------------------------")
    print("FEATURE ENGINEERING COMPLETE")
    print("Number of features:", len(final_features))
    print("Expected features:", len(MODEL_FEATURES))
    print("Wallet:", wallet)
    print("Sent transactions:", sent_count)
    print("Received transactions:", received_count)
    print("Total ETH sent:", total_sent)
    print("Total ETH received:", total_received)
    print("Total ETH balance:",
          total_received - total_sent)
    print("----------------------------------------")


    return final_features