"""Load the Olist CSVs into SQLite, then run every file in sql/ in order.
Results print to the screen and are saved to outputs/<query_name>.csv

Usage:  python run_sql.py
Needs:  pip install pandas
"""
import glob, os, sqlite3
import pandas as pd

RAW, DB = "data/raw", "olist.db"
TABLES = {
    "orders": "olist_orders_dataset.csv",
    "customers": "olist_customers_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
}
DATE_COLS = {
    "orders": ["order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date",
               "order_delivered_customer_date", "order_estimated_delivery_date"],
    "order_reviews": ["review_creation_date", "review_answer_timestamp"],
    "order_items": ["shipping_limit_date"],
}

def to_iso(series):
    """Accept 'YYYY-MM-DD HH:MM:SS' (Kaggle) or 'DD-MM-YYYY HH:MM' (some re-saved copies)
    and store everything as 'YYYY-MM-DD HH:MM:SS' so SQLite date functions work."""
    s = series.astype("string")
    parsed = pd.to_datetime(s, format="%Y-%m-%d %H:%M:%S", errors="coerce")
    parsed = parsed.fillna(pd.to_datetime(s, format="%d-%m-%Y %H:%M", errors="coerce"))
    return parsed.dt.strftime("%Y-%m-%d %H:%M:%S")

os.makedirs("outputs", exist_ok=True)
con = sqlite3.connect(DB)

if not os.path.exists(DB) or os.path.getsize(DB) < 1_000_000:
    for table, fname in TABLES.items():
        df = pd.read_csv(os.path.join(RAW, fname))
        for col in DATE_COLS.get(table, []):
            df[col] = to_iso(df[col])
        df.to_sql(table, con, if_exists="replace", index=False)
        print(f"loaded {table}: {len(df):,} rows")

bad = con.execute("""SELECT COUNT(*) FROM orders
    WHERE order_delivered_customer_date IS NOT NULL
      AND date(order_delivered_customer_date) IS NULL""").fetchone()[0]
assert bad == 0, f"{bad} delivery dates could not be read - check the date format in orders CSV"

for stmt in [
    "CREATE INDEX IF NOT EXISTS i1 ON order_items(order_id)",
    "CREATE INDEX IF NOT EXISTS i2 ON order_items(seller_id)",
    "CREATE INDEX IF NOT EXISTS i3 ON order_reviews(order_id)",
    "CREATE INDEX IF NOT EXISTS i4 ON orders(customer_id)",
    "CREATE INDEX IF NOT EXISTS i5 ON customers(customer_id)",
    "CREATE INDEX IF NOT EXISTS i6 ON products(product_id)",
    "CREATE INDEX IF NOT EXISTS i7 ON sellers(seller_id)",
    "CREATE INDEX IF NOT EXISTS i8 ON order_payments(order_id)",
]:
    con.execute(stmt)
con.commit()

for path in sorted(glob.glob("sql/*.sql")):
    name = os.path.splitext(os.path.basename(path))[0]
    sql = open(path, encoding="utf-8").read()
    if name.startswith("00_"):
        con.executescript(sql)
        print(f"\n[{name}] view created")
        continue
    df = pd.read_sql_query(sql, con)
    df.to_csv(f"outputs/{name}.csv", index=False)
    print(f"\n=== {name} ===")
    print(df.to_string(index=False))
con.close()
