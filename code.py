# slooze_analysis_final_visuals.py
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

sns.set(style="whitegrid")
plt.rcParams.update({'figure.autolayout': True})  # Prevent overlapping labels


# Load datasets

datasets = {}
for fname in ["InvoicePurchases12312016", "PurchasesFINAL12312016",
              "SalesFINAL12312016", "2017PurchasePricesDec",
              "BegInvFINAL12312016", "EndInvFINAL12312016"]:
    datasets[fname] = pd.read_csv(f"data/{fname}.csv")
 

invoicepurchase = datasets["InvoicePurchases12312016"]
purchasesfinal = datasets["PurchasesFINAL12312016"]
salesfinal = datasets["SalesFINAL12312016"]
purchaseprice = datasets["2017PurchasePricesDec"]
begin_inv = datasets["BegInvFINAL12312016"]
end_inv = datasets["EndInvFINAL12312016"]

# Clean dates & numerics

date_cols = ["InvoiceDate","PODate","PayDate","ReceivingDate","SalesDate","startDate","endDate"]
numeric_cols = ["Quantity","Dollars","SalesQuantity","SalesDollars","Price","onHand","PurchasePrice"]

for df in datasets.values():
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")


# Merge datasets safely

merged = (
    salesfinal.merge(purchasesfinal, on=["InventoryId","Store","Brand","Description","Size"], suffixes=("_sales","_purchase"), how="left")
              .merge(begin_inv, on=["InventoryId","Store","Brand","Description","Size"], suffixes=("","_begin"), how="left")
              .merge(end_inv, on=["InventoryId","Store","Brand","Description","Size"], suffixes=("","_end"), how="left")
)
merged = merged.drop_duplicates(subset=["InventoryId","Store","Brand","Description","Size"])

# Fill missing numeric values
numeric_fill = {"SalesQuantity":0, "SalesDollars":0, "SalesPrice":0, "PurchasePrice":0,
                "onHand_begin":0, "onHand_end":0}
for key in numeric_fill:
    if key in merged.columns:
        merged[key] = merged[key].fillna(numeric_fill[key])


# ABC Analysis

if "SalesPrice" not in merged.columns:
    merged["SalesPrice"] = merged["SalesDollars"] / merged["SalesQuantity"].replace(0, np.nan)
    merged["SalesPrice"].fillna(0, inplace=True)

merged["AnnualConsumptionValue"] = merged["SalesQuantity"] * merged["SalesPrice"]

abc = merged.groupby("Brand")["AnnualConsumptionValue"].sum().sort_values(ascending=False).reset_index()
abc["cum_pct"] = 100 * abc["AnnualConsumptionValue"].cumsum() / abc["AnnualConsumptionValue"].sum()

def get_category(p):
    if p <= 80:
        return "A"
    elif p <= 95:
        return "B"
    else:
        return "C"

abc["Category"] = abc["cum_pct"].apply(get_category)
merged = merged.merge(abc[["Brand","Category"]], on="Brand", how="left")

print("\nABC Category Distribution:\n", abc["Category"].value_counts())


# EOQ Calculation

ordering_cost = 100
holding_cost_rate = 0.1
merged["AnnualDemand"] = merged["SalesQuantity"] * 12
merged["HoldingCost"] = merged["SalesPrice"] * holding_cost_rate
merged["HoldingCost"] = merged["HoldingCost"].replace(0, 0.01)
merged["EOQ"] = np.sqrt((2 * merged["AnnualDemand"] * ordering_cost) / merged["HoldingCost"])

print("\nSample EOQ:\n", merged[["Brand","EOQ"]].head(10))


# Reorder Point (ROP)

lead_time_days = 7
daily_demand = merged.groupby("Brand")["SalesQuantity"].mean()
merged = merged.merge(daily_demand.rename("DailyDemand"), on="Brand", how="left")
merged["ReorderPoint"] = merged["DailyDemand"] * lead_time_days

print("\nSample Reorder Points:\n", merged[["Brand","DailyDemand","ReorderPoint"]].drop_duplicates().head(10))


# Stock Turnover

merged["AvgInventory"] = (merged.get("onHand_begin",0) + merged.get("onHand_end",0)) / 2
merged["StockTurnover"] = merged["SalesQuantity"] / merged["AvgInventory"].replace(0, np.nan)
top_turnover = merged.groupby("Brand")["StockTurnover"].mean().sort_values(ascending=False).head(10)
print("\nTop 10 Fast Moving Brands (Stock Turnover):\n", top_turnover)


# Lead Time Analysis

if "PODate" in purchasesfinal.columns and "ReceivingDate" in purchasesfinal.columns:
    purchasesfinal["LeadTimeDays"] = (purchasesfinal["ReceivingDate"] - purchasesfinal["PODate"]).dt.days
    print("\nLead Time Stats (days):")
    print(purchasesfinal["LeadTimeDays"].describe())
    long_lead_time = purchasesfinal.groupby("VendorName")["LeadTimeDays"].mean().sort_values(ascending=False).head(10)
    print("\nTop 10 Vendors with Long Lead Times:\n", long_lead_time)


# Vendor Efficiency

if "LeadTimeDays" in purchasesfinal.columns:
    vendor_efficiency = purchasesfinal.groupby("VendorName").agg({
        "Dollars":"sum",
        "LeadTimeDays":"mean"
    }).sort_values(by="Dollars", ascending=False).head(10)
    print("\nTop Vendors by Purchase $ and Lead Time:\n", vendor_efficiency)


# Monthly Sales Trend
if "SalesDate" in salesfinal.columns:
    salesfinal["Month"] = salesfinal["SalesDate"].dt.to_period("M").dt.to_timestamp()
    monthly_sales = salesfinal.groupby("Month")["SalesDollars"].sum()
    print("\nMonthly Sales Trend:\n", monthly_sales)


# Visualizations (fixed palette warning)

# ABC Category Distribution
plt.figure(figsize=(6,5))
palette_colors = {"A":"#FF9999", "B":"#99FF99", "C":"#9999FF"}  # Manual palette
sns.countplot(x="Category", data=abc.drop_duplicates(subset=["Brand"]),
              order=["A","B","C"], hue="Category", dodge=False,
              palette=palette_colors)
plt.legend([],[], frameon=False)  # Hide legend
plt.title("ABC Inventory Category Distribution", fontsize=14)
plt.xlabel("Category", fontsize=12)
plt.ylabel("Number of Brands", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()

# Top Vendors by Purchase Value
top_vendors = purchasesfinal.groupby("VendorName")["Dollars"].sum().nlargest(10)
plt.figure(figsize=(7,5))
top_vendors.plot(kind="barh", color="skyblue", edgecolor='black', width=0.6)
plt.title("Top 10 Vendors by Purchase Value", fontsize=14)
plt.xlabel("Total Purchase ($)", fontsize=12)
plt.ylabel("Vendor", fontsize=12)
plt.gca().invert_yaxis()
plt.grid(axis='x', linestyle='--', alpha=0.7)
plt.show()

# EOQ Distribution
plt.figure(figsize=(6,5))
sns.histplot(merged["EOQ"], bins=40, kde=True, color="coral")
plt.title("EOQ Distribution Across Brands", fontsize=14)
plt.xlabel("EOQ Value", fontsize=12)
plt.ylabel("Frequency", fontsize=12)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()

# Monthly Sales Trend
if "SalesDate" in salesfinal.columns:
    plt.figure(figsize=(6,5))
    plt.plot(monthly_sales.index, monthly_sales.values, marker='o', color='green', linewidth=2)
    plt.title("Monthly Sales Trend", fontsize=14)
    plt.xlabel("Month", fontsize=12)
    plt.ylabel("Total Sales ($)", fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.show()

# Top Fast Moving Brands (Stock Turnover)
plt.figure(figsize=(6,5))
top_turnover.plot(kind="bar", color="purple", width=0.6)
plt.title("Top 10 Fast Moving Brands (Stock Turnover)", fontsize=14)
plt.xlabel("Brand", fontsize=12)
plt.ylabel("Stock Turnover", fontsize=12)
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()

# Vendor Efficiency (Purchase $ vs Lead Time)
plt.figure(figsize=(10,5))
vendor_efficiency.plot(kind="bar", color=["skyblue","orange"], width=0.6)
plt.title("Top Vendors: Purchase $ vs Avg Lead Time", fontsize=14)
plt.xlabel("Vendor", fontsize=12)
plt.ylabel("Value", fontsize=12)
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.show()
