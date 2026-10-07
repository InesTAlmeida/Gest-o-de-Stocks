import pandas as pd

# Returns a simulated inventory dataframe for a hair salon
def get_mock_inventory():
    data = [
        {
            "product_id": 101,
            "product_name": "Moisturizing Shampoo 1000ml",
            "category": "Washstation",
            "stock_quantity": 8,
            "min_stock": 3,
            "cost_price": 12.50,
            "selling_price": 25.00,
        },
        {
            "product_id": 102,
            "product_name": "Intense Repair Mask 500g",
            "category": "Treatment",
            "stock_quantity": 2,
            "min_stock": 4,
            "cost_price": 15.00,
            "selling_price": 32.00,
        },
        {
            "product_id": 103,
            "product_name": "Light Brown Hair Dye 6.0",
            "category": "Hair Color",
            "stock_quantity": 0,
            "min_stock": 5,
            "cost_price": 4.20,
            "selling_price": 10.00,
        },
        {
            "product_id": 104,
            "product_name": "Argan Hair Oil 100ml",
            "category": "Styling",
            "stock_quantity": 12,
            "min_stock": 2,
            "cost_price": 8.00,
            "selling_price": 18.50,
        },
        {
            "product_id": 105,
            "product_name": "Bleaching Powder 500g",
            "category": "Hair Color",
            "stock_quantity": 1,
            "min_stock": 3,
            "cost_price": 11.00,
            "selling_price": 22.00,
        },
    ]

    df = pd.DataFrame(data)

    def calculate_status(row):
        if row["stock_quantity"] == 0:
            return "❌ Out of Stock"
        elif row["stock_quantity"] <= row["min_stock"]:
            return "⚠️ Low Stock"
        return "✅ In Stock"

    df["status"] = df.apply(calculate_status, axis=1)
    return df
