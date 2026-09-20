import os
import glob
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    roc_auc_score
)

# ============================================================
# PATHS
# ============================================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATA_DIR = os.path.join(BASE_DIR, "data")
MODEL_PATH = os.path.join(
    BASE_DIR,
    "backend",
    "ml",
    "fraud_model.pkl"
)

# ============================================================
# FIND DATASET
# ============================================================

csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

if not csv_files:
    raise FileNotFoundError(
        f"No CSV dataset found in {DATA_DIR}"
    )

DATASET_PATH = csv_files[0]

print("=" * 60)
print("CRYPTO FRAUD ML TRAINING")
print("=" * 60)

print("\nDataset:")
print(DATASET_PATH)

# ============================================================
# LOAD DATASET
# ============================================================

print("\nLoading dataset...")

df = pd.read_csv(DATASET_PATH)

print("Dataset loaded successfully.")
print(f"Rows: {df.shape[0]}")
print(f"Columns: {df.shape[1]}")

# ============================================================
# TARGET
# ============================================================

TARGET_COLUMN = "FLAG"

if TARGET_COLUMN not in df.columns:
    raise ValueError(
        f"Target column '{TARGET_COLUMN}' not found."
    )

# ============================================================
# REMOVE NON-ML COLUMNS
# ============================================================

# These columns are identifiers, not behavioral features.
columns_to_remove = [
    "FLAG",
    "Address",
    "Unnamed: 0",
    "Index",
    " ERC20 most sent token type",
    "ERC20 most sent token type",
    "ERC20_most_rec_token_type"
]

columns_to_remove = [
    col for col in columns_to_remove
    if col in df.columns
]

X = df.drop(columns=columns_to_remove)
y = df[TARGET_COLUMN]

# ============================================================
# CONVERT FEATURES TO NUMERIC
# ============================================================

print("\nPreparing features...")

X = X.apply(pd.to_numeric, errors="coerce")

# Replace infinity values
X = X.replace([float("inf"), float("-inf")], pd.NA)

# Fill missing values
X = X.fillna(0)

# ============================================================
# FEATURE INFORMATION
# ============================================================

feature_names = list(X.columns)

print(f"\nNumber of ML features: {len(feature_names)}")

print("\nFeatures being used:")

for i, feature in enumerate(feature_names, start=1):
    print(f"{i}. {feature}")

# ============================================================
# TARGET DISTRIBUTION
# ============================================================

print("\nTarget distribution:")
print(y.value_counts())

# ============================================================
# TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y
)

print("\nTraining samples:", len(X_train))
print("Testing samples:", len(X_test))

# ============================================================
# RANDOM FOREST
# ============================================================

print("\nTraining Random Forest model...")

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=None,
    min_samples_split=2,
    min_samples_leaf=1,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# ============================================================
# PREDICTIONS
# ============================================================

y_pred = model.predict(X_test)

y_probability = model.predict_proba(X_test)[:, 1]

# ============================================================
# MODEL EVALUATION
# ============================================================

accuracy = accuracy_score(y_test, y_pred)

roc_auc = roc_auc_score(
    y_test,
    y_probability
)

print("\n")
print("=" * 60)
print("MODEL RESULTS")
print("=" * 60)

print(f"\nAccuracy: {accuracy:.4f}")
print(f"ROC-AUC: {roc_auc:.4f}")

print("\nClassification Report:")

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "Normal",
            "Fraud"
        ]
    )
)

print("\nConfusion Matrix:")

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)

# ============================================================
# FEATURE IMPORTANCE
# ============================================================

importance_df = pd.DataFrame({
    "feature": feature_names,
    "importance": model.feature_importances_
})

importance_df = importance_df.sort_values(
    by="importance",
    ascending=False
)

print("\nTop 15 Important Features:")

print(
    importance_df.head(15).to_string(
        index=False
    )
)

# ============================================================
# SAVE MODEL
# ============================================================

model_package = {
    "model": model,
    "features": feature_names
}

joblib.dump(
    model_package,
    MODEL_PATH
)

print("\n")
print("=" * 60)
print("MODEL SAVED SUCCESSFULLY")
print("=" * 60)

print("\nModel location:")
print(MODEL_PATH)

print("\nModel is ready for integration with FastAPI.")