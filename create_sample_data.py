import os
import pandas as pd

SOURCE_FOLDER = "data"
OUTPUT_FOLDER = "sample_data"

os.makedirs(OUTPUT_FOLDER, exist_ok=True)

FILES = {
    "InvoicePurchases12312016.csv": 1000,
    "PurchasesFINAL12312016.csv": 1000,
    "SalesFINAL12312016.csv": 2000,
    "2017PurchasePricesDec.csv": None,   # keep complete
    "BegInvFINAL12312016.csv": 1000,
    "EndInvFINAL12312016.csv": 1000,
}

print("=" * 50)
print("Creating Sample Datasets")
print("=" * 50)

for filename, rows in FILES.items():

    path = os.path.join(SOURCE_FOLDER, filename)

    if not os.path.exists(path):
        print(f"❌ Missing: {filename}")
        continue

    df = pd.read_csv(path)

    if rows is not None and len(df) > rows:
        sample = df.sample(rows, random_state=42)
    else:
        sample = df.copy()

    sample.to_csv(
        os.path.join(OUTPUT_FOLDER, filename),
        index=False
    )

    print(f"✓ {filename}  ({len(sample)} rows)")

print("\nFinished!")