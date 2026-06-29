# dashboard.py

import os
import numpy as np
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(
    page_title="Inventory Analytics Dashboard",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Inventory Analytics BI Dashboard")


# ==================================================
# LOAD DATA
# ==================================================

@st.cache_data
def load_data():

    folder = "sample_data"

    files = {
        "sales": "SalesFINAL12312016.csv",
        "purchases": "PurchasesFINAL12312016.csv",
        "begin_inv": "BegInvFINAL12312016.csv",
        "end_inv": "EndInvFINAL12312016.csv",
        "prices": "2017PurchasePricesDec.csv"
    }

    data = {}

    for key, filename in files.items():

        path = os.path.join(folder, filename)

        if not os.path.exists(path):
            st.error(f"Missing file: {path}")
            st.stop()

        data[key] = pd.read_csv(path)

    return data


data = load_data()

sales = data["sales"]
purchases = data["purchases"]
begin_inv = data["begin_inv"]
end_inv = data["end_inv"]


# ==================================================
# CLEAN DATA
# ==================================================

for df in data.values():

    if "SalesDate" in df.columns:
        df["SalesDate"] = pd.to_datetime(
            df["SalesDate"],
            errors="coerce"
        )

    if "PODate" in df.columns:
        df["PODate"] = pd.to_datetime(
            df["PODate"],
            errors="coerce"
        )

    if "ReceivingDate" in df.columns:
        df["ReceivingDate"] = pd.to_datetime(
            df["ReceivingDate"],
            errors="coerce"
        )


numeric_cols = [
    "SalesQuantity",
    "SalesDollars",
    "SalesPrice",
    "PurchasePrice",
    "onHand"
]

for col in numeric_cols:

    if col in sales.columns:
        sales[col] = pd.to_numeric(
            sales[col],
            errors="coerce"
        )

    if col in purchases.columns:
        purchases[col] = pd.to_numeric(
            purchases[col],
            errors="coerce"
        )


sales.fillna(0, inplace=True)
purchases.fillna(0, inplace=True)


# ==================================================
# BRAND ANALYSIS
# ==================================================

brand_sales = (

    sales.groupby("Brand", as_index=False)

    .agg({
        "SalesQuantity": "sum",
        "SalesDollars": "sum"
    })

)

brand_sales = brand_sales.sort_values(
    "SalesDollars",
    ascending=False
)


brand_sales["cum_pct"] = (

    brand_sales["SalesDollars"]

    .cumsum()

    /

    brand_sales["SalesDollars"].sum()

    * 100

)


def abc_category(x):

    if x <= 80:
        return "A"

    elif x <= 95:
        return "B"

    return "C"


brand_sales["Category"] = brand_sales[
    "cum_pct"
].apply(abc_category)

# ==================================================
# SIDEBAR
# ==================================================

st.sidebar.header("Filters")

selected_category = st.sidebar.multiselect(
    "ABC Category",
    ["A", "B", "C"],
    default=["A", "B", "C"]
)

filtered = brand_sales[
    brand_sales["Category"].isin(selected_category)
].copy()

# Convert Brand to string everywhere for consistency
filtered["Brand"] = filtered["Brand"].astype(str)

brand_options = sorted(filtered["Brand"].unique())

selected_brand = st.sidebar.multiselect(
    "Brand",
    brand_options
)

if selected_brand:
    filtered = filtered[
        filtered["Brand"].isin(selected_brand)
    ]

# ==================================================
# KPIs
# ==================================================

st.subheader("Key Metrics")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Revenue",
    f"${filtered['SalesDollars'].sum():,.0f}"
)

col2.metric(
    "Quantity Sold",
    f"{filtered['SalesQuantity'].sum():,.0f}"
)

avg_price = 0

if filtered["SalesQuantity"].sum() > 0:

    avg_price = (

        filtered["SalesDollars"].sum()

        /

        filtered["SalesQuantity"].sum()

    )

col3.metric(
    "Avg Selling Price",
    f"${avg_price:.2f}"
)

col4.metric(
    "Brands",
    filtered["Brand"].nunique()
)


# ==================================================
# ABC DISTRIBUTION
# ==================================================

st.subheader("📊 ABC Category Distribution")

abc_counts = (
    filtered["Category"]
    .value_counts()
    .reset_index()
)

abc_counts.columns = ["Category", "Count"]

fig = px.bar(
    abc_counts,
    x="Category",
    y="Count",
    color="Category",
    title="ABC Category Distribution"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# TOP BRANDS
# ==================================================

st.subheader("🏆 Top 10 Brands by Revenue")

top10 = filtered.head(10)

fig = px.bar(
    top10,
    x="Brand",
    y="SalesDollars",
    color="SalesDollars"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# FAST MOVING BRANDS
# ==================================================

st.subheader("⚡ Top 10 Fast Moving Brands")

fast = filtered.sort_values(
    "SalesQuantity",
    ascending=False
).head(10)

fig = px.bar(
    fast,
    x="Brand",
    y="SalesQuantity",
    color="SalesQuantity"
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# EOQ
# ==================================================

st.subheader("📦 EOQ Distribution")

EOQ_ORDERING_COST = 100
HOLDING_RATE = 0.1

filtered = filtered.copy()

filtered["EOQ"] = np.sqrt(
    2
    * filtered["SalesQuantity"]
    * EOQ_ORDERING_COST
    /
    (avg_price * HOLDING_RATE + 0.01)
)

fig = px.histogram(
    filtered,
    x="EOQ",
    nbins=20
)

st.plotly_chart(
    fig,
    use_container_width=True
)


# ==================================================
# MONTHLY SALES
# ==================================================

if "SalesDate" in sales.columns:

    st.subheader("📈 Monthly Sales Trend")

    monthly = sales.copy()

    monthly["Month"] = (

        monthly["SalesDate"]

        .dt.to_period("M")

        .astype(str)

    )

    monthly_sales = (

        monthly.groupby("Month")["SalesDollars"]

        .sum()

        .reset_index()

    )

    fig = px.line(
        monthly_sales,
        x="Month",
        y="SalesDollars",
        markers=True
    )

    st.plotly_chart(
        fig,
        use_container_width=True
    )


# ==================================================
# INSIGHTS
# ==================================================

st.subheader("Business Insights")

if len(filtered) > 0:

    best_brand = filtered.iloc[0]["Brand"]

    fastest_brand = fast.iloc[0]["Brand"]

    st.success(
        f"Most Profitable Brand: {best_brand}"
    )

    st.info(
        f"⚡ Fastest Moving Brand: {fastest_brand}"
    )


# ==================================================
# DEBUG
# ==================================================

with st.expander("🔍 Debug Information"):

    st.write("Sales Shape:", sales.shape)
    st.write("Purchases Shape:", purchases.shape)
    st.write(filtered.head())


st.success("Dashboard Loaded Successfully")