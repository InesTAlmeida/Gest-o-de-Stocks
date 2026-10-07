import io
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import streamlit as st

# Import mock data function
from mock_data import get_mock_inventory

# PAGE CONFIGURATION & STYLES

st.set_page_config(
    page_title="Stock Management - Hair Salon (Demo)",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }
        div.stButton > button {
            width: 100%;
            border-radius: 8px;
            height: 3rem;
            font-weight: bold;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
        }
        @media (max-width: 640px) {
            [data-testid="column"] {
                width: 100% !important;
                flex: 1 1 100% !important;
                min-width: 100% !important;
            }
        }
    </style>
""",
    unsafe_allow_html=True,
)

# DATA LOADING & SESSION STATE MANAGEMENT

if "df_stocks" not in st.session_state:
    st.session_state.df_stocks = get_mock_inventory()

    st.session_state.df_invoices = pd.DataFrame([
        {
            "Date": "15-09-2026",
            "Invoice №": "INV 2026/102",
            "Supplier": "L'Oréal Pro",
            "Product": "Moisturizing Shampoo 1000ml",
            "Quantity": 10,
            "Unit Price (€)": 12.50,
            "Batch": "LOT-9921",
            "Expiry Date": "12-2027",
        },
        {
            "Date": "20-09-2026",
            "Invoice №": "INV 2026/884",
            "Supplier": "Wella Professionals",
            "Product": "Light Brown Hair Dye 6.0",
            "Quantity": 5,
            "Unit Price (€)": 4.20,
            "Batch": "LOT-3310",
            "Expiry Date": "08-2028",
        },
        {
            "Date": "28-09-2026",
            "Invoice №": "INV 2026/401",
            "Supplier": "Schwarzkopf",
            "Product": "Intense Repair Mask 500g",
            "Quantity": 4,
            "Unit Price (€)": 15.00,
            "Batch": "LOT-1049",
            "Expiry Date": "05-2027",
        },
    ])

    st.session_state.df_movements = pd.DataFrame([
        {
            "Date": "01-10-2026",
            "Product": "Moisturizing Shampoo 1000ml",
            "Quantity": 2,
            "Reason": "Client Service",
        },
        {
            "Date": "02-10-2026",
            "Product": "Intense Repair Mask 500g",
            "Quantity": 1,
            "Reason": "Client Service",
        },
        {
            "Date": "03-10-2026",
            "Product": "Argan Hair Oil 100ml",
            "Quantity": 1,
            "Reason": "Retail Sale",
        },
    ])

df_stocks = st.session_state.df_stocks


def convert_to_excel(df):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Stock")
    return output.getvalue()


# HEADER

st.title("📦 Inventory Management System — Hair Salon")
st.caption("Portfolio Demonstration Version (Mock Data)")

# SIDEBAR (DEMO OPERATIVE ACTIONS)

st.sidebar.title("Settings (Demo Mode)")

with st.sidebar.expander("📥 Restock (Invoice / Purchase)", expanded=False):
    with st.form(key="new_purchase"):
        inv_number = st.text_input("Invoice №", value="INV 2026/999")
        supplier = st.text_input("Supplier", value="L'Oréal Pro")
        product_name = st.text_input(
            "Product Name", value="Moisturizing Shampoo 1000ml"
        )
        category = st.text_input("Category", value="Washstation")
        qty = st.number_input("Purchased Qty", min_value=1, value=5)
        cost_un = st.number_input("Unit Cost (€)", min_value=0.0, value=12.5)
        sell_un = st.number_input(
            "Retail Price (€)", min_value=0.0, value=25.0
        )

        submitted = st.form_submit_button("Add Stock")

if submitted:
    if product_name in st.session_state.df_stocks["product_name"].values:
        idx = st.session_state.df_stocks[
            st.session_state.df_stocks["product_name"] == product_name
        ].index[0]
        st.session_state.df_stocks.at[idx, "stock_quantity"] += qty
    else:
        new_row = pd.DataFrame([{
            "product_id": 999,
            "product_name": product_name,
            "category": category,
            "stock_quantity": qty,
            "min_stock": 3,
            "cost_price": cost_un,
            "selling_price": sell_un,
            "status": "✅ In Stock",
        }])
        st.session_state.df_stocks = pd.concat(
            [st.session_state.df_stocks, new_row], ignore_index=True
        )
    st.sidebar.success("Stock entry logged in memory!")
    st.rerun()

with st.sidebar.expander("📤 Stock Usage / Sales"):
    if not df_stocks.empty:
        prod_usage = st.selectbox(
            "Product:", df_stocks["product_name"].unique()
        )
        qty_usage = st.number_input("Qty to Remove:", min_value=1, value=1)
        if st.button("Confirm Stock Out"):
            idx = st.session_state.df_stocks[
                st.session_state.df_stocks["product_name"] == prod_usage
            ].index[0]
            current_qty = st.session_state.df_stocks.at[idx, "stock_quantity"]
            st.session_state.df_stocks.at[idx, "stock_quantity"] = max(
                0, current_qty - qty_usage
            )
            st.success(f"Registered stock reduction for {prod_usage}!")
            st.rerun()

# KPI METRICS / FINANCIAL SUMMARY

total_products = len(df_stocks)
alerts_count = len(
    df_stocks[df_stocks["stock_quantity"] <= df_stocks["min_stock"]]
)
total_cost_value = (
    df_stocks["stock_quantity"] * df_stocks["cost_price"]
).sum()
total_sales_value = (
    df_stocks["stock_quantity"] * df_stocks["selling_price"]
).sum()
potential_profit = total_sales_value - total_cost_value

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Products", total_products)
col2.metric("Low Stock Alerts", alerts_count, delta_color="inverse")
col3.metric("Stock Investment", f"{total_cost_value:.2f} €")
col4.metric("Potential Profit", f"{potential_profit:.2f} €")

st.divider()

# NAVIGATION TABS

(
    tab_stock,
    tab_margins,
    tab_batches,
    tab_movements,
    tab_purchases,
    tab_dashboard,
) = st.tabs([
    "📦 Available Stock",
    "💰 Prices & Margins",
    "🔍 Batches & Expiry",
    "📋 Usage History",
    "📥 Purchase History",
    "📊 Analytics Dashboard",
])

# --- TAB 1: AVAILABLE STOCK ---
with tab_stock:
    st.subheader("📋 Inventory & Stock Control")

    categories = ["All"] + list(df_stocks["category"].unique())
    selected_cat = st.selectbox("Filter by Category:", categories)

    df_display = df_stocks.copy()
    if selected_cat != "All":
        df_display = df_display[df_display["category"] == selected_cat]

    def highlight_stock(row):
        qty = row.get("stock_quantity", 0)
        min_st = row.get("min_stock", 3)
        if qty == 0:
            return ["background-color: #ffcccc; color: black"] * len(row)
        elif qty <= min_st:
            return ["background-color: #ffffcc; color: black"] * len(row)
        return [""] * len(row)

    try:
        st.dataframe(
            df_display.style.apply(highlight_stock, axis=1),
            use_container_width=True,
            hide_index=True,
        )
    except Exception:
        st.dataframe(df_display, use_container_width=True, hide_index=True)

    st.caption("🔴 Red: Out of Stock | 🟡 Yellow: Low Stock Alert")

    st.download_button(
        label="📥 Download Stock Data (Excel)",
        data=convert_to_excel(df_display),
        file_name=f"Stock_{datetime.today().strftime('%Y-%m-%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

# --- TAB 2: PRICES & MARGINS ---
with tab_margins:
    st.subheader("💰 Price & Margin Analysis")
    df_fin = df_stocks.copy()
    df_fin["unit_margin"] = df_fin["selling_price"] - df_fin["cost_price"]
    df_fin["total_profit"] = df_fin["unit_margin"] * df_fin["stock_quantity"]

    st.dataframe(
        df_fin[[
            "product_name",
            "category",
            "cost_price",
            "selling_price",
            "unit_margin",
            "total_profit",
        ]],
        use_container_width=True,
        column_config={
            "product_name": "Product",
            "category": "Category",
            "cost_price": st.column_config.NumberColumn(
                "Cost Price (€)", format="%.2f €"
            ),
            "selling_price": st.column_config.NumberColumn(
                "Selling Price (€)", format="%.2f €"
            ),
            "unit_margin": st.column_config.NumberColumn(
                "Unit Margin (€)", format="%.2f €"
            ),
            "total_profit": st.column_config.NumberColumn(
                "Potential Profit (€)", format="%.2f €"
            ),
        },
        hide_index=True,
    )

# --- TAB 3: BATCHES & EXPIRY ---
with tab_batches:
    st.subheader("🔍 Batches & Expiry Dates")
    st.dataframe(
        st.session_state.df_invoices[[
            "Product",
            "Supplier",
            "Invoice №",
            "Batch",
            "Expiry Date",
        ]],
        use_container_width=True,
        hide_index=True,
    )

# --- TAB 4: USAGE HISTORY ---
with tab_movements:
    st.subheader("📋 Stock Output History")
    st.dataframe(
        st.session_state.df_movements,
        use_container_width=True,
        hide_index=True,
    )

# --- TAB 5: PURCHASE HISTORY ---
with tab_purchases:
    st.subheader("📥 Purchase & Invoicing Log")
    st.dataframe(
        st.session_state.df_invoices,
        use_container_width=True,
        hide_index=True,
    )

# --- TAB 6: VISUAL DASHBOARD ---
with tab_dashboard:
    st.subheader("📊 Analytics & Visual Dashboard")
    c1, c2 = st.columns(2)

    with c1:
        fig_pie = px.pie(
            df_stocks,
            values="stock_quantity",
            names="category",
            title="Stock Volume by Category",
            hole=0.4,
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    with c2:
        df_stocks["investment"] = (
            df_stocks["stock_quantity"] * df_stocks["cost_price"]
        )
        fig_bar = px.bar(
            df_stocks,
            x="product_name",
            y="investment",
            color="category",
            labels={"product_name": "Product", "investment": "Total Value (€)"},
            title="Capital Tied Up per Product (€)",
        )
        st.plotly_chart(fig_bar, use_container_width=True)
