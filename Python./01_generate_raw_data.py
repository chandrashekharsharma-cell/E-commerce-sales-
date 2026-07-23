"""
01_generate_raw_data.py
------------------------
Generates realistic synthetic e-commerce data for "NovaCart", a fictional
Indian online retail marketplace. Data is deliberately messy (duplicates,
inconsistent casing, missing values) to simulate a real OLTP export that
needs cleaning in the ETL step (02_etl_pipeline.py).

Output: data/raw/customers_raw.csv, products_raw.csv, orders_raw.csv, order_items_raw.csv
"""
import numpy as np
import pandas as pd
from datetime import date, timedelta
import random

SEED = 42
np.random.seed(SEED)
random.seed(SEED)

OUT = "data/raw"

# ---------------------------------------------------------------------------
# Reference lists
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Aarav","Vivaan","Aditya","Vihaan","Arjun","Reyansh","Krishna","Ishaan","Rohan","Karan",
    "Rahul","Aryan","Dhruv","Kabir","Sai","Aakash","Nikhil","Varun","Siddharth","Rajesh",
    "Sanjay","Vikram","Mohammed","Imran","Farhan","Zaid","Arun","Deepak","Manoj","Anand",
    "Ganesh","Praveen","Naveen","Ravi","Ajay","Vijay","Amit","Sandeep","Suresh","Irfan",
    "Aadhya","Ananya","Diya","Ishita","Kavya","Myra","Sara","Anika","Riya","Priya",
    "Neha","Pooja","Sneha","Divya","Shreya","Meera","Kritika","Nisha","Swati","Anjali",
    "Deepika","Kavita","Sunita","Rekha","Fatima","Ayesha","Zara","Sana","Lakshmi","Radha",
    "Geeta","Manisha","Preeti","Simran","Gurpreet","Harleen","Aisha","Pallavi","Shalini","Nandini",
]
LAST_NAMES = [
    "Sharma","Verma","Gupta","Singh","Kumar","Patel","Reddy","Rao","Nair","Menon",
    "Iyer","Iyengar","Pillai","Chatterjee","Banerjee","Mukherjee","Das","Bose","Khan","Ali",
    "Sheikh","Ahmed","Malhotra","Kapoor","Chopra","Mehta","Shah","Joshi","Desai","Trivedi",
    "Yadav","Chauhan","Rathore","Bhatt","Agarwal","Bansal","Jain","Saxena","Mishra","Tiwari","Pandey",
]
EMAIL_DOMAINS = ["gmail.com","yahoo.com","outlook.com","rediffmail.com","hotmail.com"]

CITY_STATE_REGION = [
    ("Mumbai","Maharashtra","West"), ("Pune","Maharashtra","West"), ("Nagpur","Maharashtra","West"),
    ("Ahmedabad","Gujarat","West"), ("Surat","Gujarat","West"), ("Jaipur","Rajasthan","North"),
    ("Delhi","Delhi","North"), ("Chandigarh","Punjab","North"), ("Amritsar","Punjab","North"),
    ("Lucknow","Uttar Pradesh","North"), ("Kanpur","Uttar Pradesh","North"),
    ("Bengaluru","Karnataka","South"), ("Mysuru","Karnataka","South"),
    ("Chennai","Tamil Nadu","South"), ("Coimbatore","Tamil Nadu","South"),
    ("Hyderabad","Telangana","South"), ("Kochi","Kerala","South"),
    ("Kolkata","West Bengal","East"), ("Bhubaneswar","Odisha","East"), ("Patna","Bihar","East"),
    ("Ranchi","Jharkhand","East"),
    ("Bhopal","Madhya Pradesh","Central"), ("Indore","Madhya Pradesh","Central"),
    ("Jabalpur","Madhya Pradesh","Central"), ("Raipur","Chhattisgarh","Central"),
    ("Guwahati","Assam","Northeast"), ("Shillong","Meghalaya","Northeast"),
]
CITY_WEIGHTS = np.array([14,7,3, 6,3, 5, 12,3,2, 5,3, 10,2, 8,3, 7,3, 6,2,2,2, 3,4,2,2, 2,1], dtype=float)
CITY_WEIGHTS = CITY_WEIGHTS / CITY_WEIGHTS.sum()

CATEGORIES = {
    "Electronics": (["Smartphones","Laptops","Headphones","Smart Watches","Cameras","Bluetooth Speakers"], 2000, 80000),
    "Fashion & Apparel": (["Men Shirts","Women Kurtas","Jeans","Ethnic Wear","Footwear","Winterwear"], 400, 4500),
    "Home & Kitchen": (["Cookware","Storage Solutions","Small Appliances","Home Decor","Bedding"], 300, 12000),
    "Beauty & Personal Care": (["Skincare","Haircare","Makeup","Fragrances","Grooming"], 150, 3500),
    "Grocery & Gourmet": (["Snacks","Beverages","Staples","Organic Foods","Spices"], 50, 1500),
    "Sports & Fitness": (["Yoga Gear","Cricket Gear","Gym Equipment","Cycling","Running Gear"], 300, 15000),
    "Mobile & Accessories": (["Phone Cases","Chargers","Power Banks","Screen Guards","Cables"], 150, 2500),
    "Books & Stationery": (["Fiction","Non-fiction","Notebooks","Office Supplies","Kids Books"], 80, 1200),
    "Furniture": (["Chairs","Study Tables","Storage Units","Sofas","Bedroom Sets"], 1500, 45000),
    "Baby & Toys": (["Toys","Baby Care","Educational Kits","Outdoor Play"], 200, 5000),
}
BRANDS = ["Zynovo","Urbane","CraftHouse","PixelPro","GlowNest","Vivara","TrueFit","Everstone",
          "Nimbus","Solace","Kadenza","Brightlane","Roamly","Fernweh","Northstead","Meadowlace",
          "Corvid","Halcyon","Amberline","Cirrus"]
ADJECTIVES = ["Classic","Premium","Everyday","Pro","Compact","Deluxe","Essential","Signature","Urban","Comfort"]

CHANNELS = ["Website","Mobile App","Marketplace","Social Commerce"]
CHANNEL_WEIGHTS = [0.45, 0.35, 0.15, 0.05]
PAYMENT_METHODS = ["UPI","Credit Card","Debit Card","Net Banking","Cash on Delivery","Wallet"]
PAYMENT_WEIGHTS = [0.38, 0.18, 0.14, 0.08, 0.14, 0.08]
ORDER_STATUSES = ["Delivered","Returned","Cancelled"]
STATUS_WEIGHTS = [0.86, 0.08, 0.06]

START_DATE = date(2023, 6, 1)
END_DATE = date(2026, 6, 30)
N_DAYS = (END_DATE - START_DATE).days

N_CUSTOMERS = 4000
N_PRODUCTS = 180
N_ORDERS = 30000


def capped_pareto_weights(n, a=3.2, cap_multiple=6.0):
    """Skewed-but-bounded popularity weights: heavier hitters exist, but no
    single item/customer can run away with an unrealistic share of the total."""
    w = np.random.pareto(a, size=n) + 0.2
    cap = cap_multiple * w.mean()
    w = np.clip(w, None, cap)
    return w / w.sum()


def rand_dates(n, start, n_days, growth=True):
    """Sample n dates with a mild upward trend + festive-season & weekend seasonality."""
    day_offsets = np.arange(n_days)
    # base upward trend (business growth)
    trend = np.linspace(1.0, 2.0, n_days) if growth else np.ones(n_days)
    dates_full = [start + timedelta(days=int(d)) for d in day_offsets]
    month_boost = np.array([1.6 if d.month in (10, 11) else 1.3 if d.month == 12 else
                             0.85 if d.month == 2 else 1.0 for d in dates_full])
    weekend_boost = np.array([1.35 if d.weekday() >= 5 else 1.0 for d in dates_full])
    weights = trend * month_boost * weekend_boost
    weights = weights / weights.sum()
    chosen = np.random.choice(day_offsets, size=n, p=weights)
    return [start + timedelta(days=int(d)) for d in chosen]


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------
signup_dates = rand_dates(N_CUSTOMERS, START_DATE, N_DAYS, growth=True)
city_idx = np.random.choice(len(CITY_STATE_REGION), size=N_CUSTOMERS, p=CITY_WEIGHTS)

rows = []
for i in range(1, N_CUSTOMERS + 1):
    fn = random.choice(FIRST_NAMES)
    ln = random.choice(LAST_NAMES)
    gender = random.choice(["Male", "Female"])
    age = int(np.clip(np.random.normal(33, 9), 18, 70))
    birth_year = date.today().year - age
    city, state, region = CITY_STATE_REGION[city_idx[i - 1]]
    email = f"{fn.lower()}.{ln.lower()}{random.randint(1,999)}@{random.choice(EMAIL_DOMAINS)}"

    # inject messiness
    name_case = random.random()
    if name_case < 0.06:
        fn, ln = fn.upper(), ln.upper()
    elif name_case < 0.10:
        fn, ln = f"  {fn} ", ln.lower()

    if random.random() < 0.02:
        email = ""
    if random.random() < 0.015:
        city = None

    rows.append({
        "customer_id": f"CUST{i:05d}",
        "first_name": fn,
        "last_name": ln,
        "email": email,
        "gender": gender if random.random() > 0.01 else gender.upper(),
        "birth_year": birth_year,
        "city": city,
        "state": state if city else None,
        "region": region if city else None,
        "signup_date": signup_dates[i - 1].isoformat(),
    })

customers_df = pd.DataFrame(rows)
# introduce ~1% exact duplicate rows (common OLTP export issue)
dupes = customers_df.sample(frac=0.01, random_state=SEED)
customers_df = pd.concat([customers_df, dupes], ignore_index=True)
customers_df.to_csv(f"{OUT}/customers_raw.csv", index=False)

# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------
rows = []
pid = 1
cats = list(CATEGORIES.keys())
per_cat = N_PRODUCTS // len(cats)
for cat, (subcats, lo, hi) in CATEGORIES.items():
    for _ in range(per_cat):
        sub = random.choice(subcats)
        brand = random.choice(BRANDS)
        adj = random.choice(ADJECTIVES)
        name = f"{brand} {adj} {sub}"
        price = float(np.round(np.random.lognormal(mean=np.log((lo + hi) / 2), sigma=0.35), -1))
        price = float(np.clip(price, lo, hi))
        cost_ratio = np.random.uniform(0.45, 0.70)
        cost = round(price * cost_ratio, 2)
        launch = START_DATE - timedelta(days=random.randint(0, 900))
        rows.append({
            "product_id": f"PROD{pid:04d}",
            "product_name": name,
            "category": cat,
            "sub_category": sub,
            "brand": brand,
            "unit_price": price,
            "cost_price": cost,
            "launch_date": launch.isoformat(),
        })
        pid += 1
products_df = pd.DataFrame(rows)
products_df.to_csv(f"{OUT}/products_raw.csv", index=False)

# ---------------------------------------------------------------------------
# Orders (header) — with repeat-customer power-law behaviour
# ---------------------------------------------------------------------------
# assign a "loyalty weight" per customer so some customers order far more than others
customer_ids = customers_df["customer_id"].unique()
loyalty_weight = capped_pareto_weights(len(customer_ids), a=3.5, cap_multiple=5.0)

order_dates = rand_dates(N_ORDERS, START_DATE, N_DAYS, growth=True)
order_customers = np.random.choice(customer_ids, size=N_ORDERS, p=loyalty_weight)
order_channels = np.random.choice(CHANNELS, size=N_ORDERS, p=CHANNEL_WEIGHTS)
order_payments = np.random.choice(PAYMENT_METHODS, size=N_ORDERS, p=PAYMENT_WEIGHTS)
order_statuses = np.random.choice(ORDER_STATUSES, size=N_ORDERS, p=STATUS_WEIGHTS)

rows = []
for i in range(N_ORDERS):
    channel_raw = order_channels[i]
    if random.random() < 0.05:
        channel_raw = channel_raw.upper() if random.random() < 0.5 else channel_raw.lower()
    rows.append({
        "order_id": f"ORD{i+1:07d}",
        "customer_id": order_customers[i],
        "order_date": order_dates[i].isoformat(),
        "channel": channel_raw,
        "payment_method": order_payments[i],
        "order_status": order_statuses[i],
        "shipping_cost": round(float(np.random.choice([0, 0, 0, 29, 49, 79], p=[0.5,0.1,0.05,0.15,0.12,0.08])), 2),
    })
orders_df = pd.DataFrame(rows)
orders_df.to_csv(f"{OUT}/orders_raw.csv", index=False)

# ---------------------------------------------------------------------------
# Order items (line-item grain)
# ---------------------------------------------------------------------------
product_ids = products_df["product_id"].values
product_prices = dict(zip(products_df["product_id"], products_df["unit_price"]))
# skew popularity: some products sell far more than others
prod_pop = capped_pareto_weights(len(product_ids), a=3.0, cap_multiple=5.0)

rows = []
item_id = 1
n_items_per_order = np.random.choice([1, 2, 3, 4, 5], size=N_ORDERS, p=[0.42, 0.28, 0.16, 0.09, 0.05])
for oi, order_id in enumerate(orders_df["order_id"].values):
    n_items = n_items_per_order[oi]
    chosen_products = np.random.choice(product_ids, size=n_items, replace=False, p=prod_pop)
    for prod in chosen_products:
        qty = int(np.random.choice([1, 2, 3], p=[0.7, 0.22, 0.08]))
        discount = float(np.random.choice([0, 5, 10, 15, 20, 25], p=[0.40, 0.12, 0.20, 0.14, 0.09, 0.05]))
        base_price = product_prices[prod]
        # small chance of a data-entry glitch (negative qty) to be cleaned in ETL
        if random.random() < 0.003:
            qty = -qty
        rows.append({
            "order_item_id": f"OI{item_id:08d}",
            "order_id": order_id,
            "product_id": prod,
            "quantity": qty,
            "discount_pct": discount if random.random() > 0.02 else None,
            "unit_price_at_sale": base_price,
        })
        item_id += 1
order_items_df = pd.DataFrame(rows)
# a handful of accidental exact-duplicate line items (double-scan at checkout)
dupes = order_items_df.sample(frac=0.004, random_state=SEED)
order_items_df = pd.concat([order_items_df, dupes], ignore_index=True)
order_items_df.to_csv(f"{OUT}/order_items_raw.csv", index=False)

print("Raw data generated:")
print(f"  customers_raw.csv    : {len(customers_df):,} rows")
print(f"  products_raw.csv     : {len(products_df):,} rows")
print(f"  orders_raw.csv       : {len(orders_df):,} rows")
print(f"  order_items_raw.csv  : {len(order_items_df):,} rows")
