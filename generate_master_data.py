"""Generate master-data CSVs (customer, subscription, vehicle) for BigQuery import.

Run: python generate_master_data.py
Output: customer_master.csv, subscription_master.csv, vehicle_master.csv at repo root.
"""

import csv
import random
from pathlib import Path

from src.generator.factory import _make_vin

ROOT = Path(__file__).resolve().parent
SEED = 42
VINS_PER_SUB = 100

# (customer_id, customer_name, street_address, city, state, pincode)
CUSTOMERS = [
    ("CUST001", "Bharat Transports Ltd",    "47, Industrial Area Phase 1, Andheri East", "Mumbai",    "Maharashtra",   "400072"),
    ("CUST002", "Hindustan Transports Ltd", "12, Connaught Circus, Block A",             "Delhi",     "Delhi",         "110001"),
    ("CUST003", "Maharaja Transports Ltd",  "208, MG Road, Indiranagar",                 "Bangalore", "Karnataka",     "560038"),
    ("CUST004", "Shakti Transports Ltd",    "55, Anna Salai, T Nagar",                   "Chennai",   "Tamil Nadu",    "600017"),
    ("CUST005", "Vijay Transports Ltd",     "3B, Sector V, Salt Lake",                   "Kolkata",   "West Bengal",   "700091"),
    ("CUST006", "Ganga Transports Ltd",     "78, Hitech City Main Road",                 "Hyderabad", "Telangana",     "500081"),
    ("CUST007", "Krishna Transports Ltd",   "21, Hinjewadi Phase 2, Wakad Road",         "Pune",      "Maharashtra",   "411057"),
    ("CUST008", "Vishal Transports Ltd",    "104, SG Highway, Bodakdev",                 "Ahmedabad", "Gujarat",       "380054"),
    ("CUST009", "Padma Transports Ltd",     "9, Malviya Nagar, JLN Marg",                "Jaipur",    "Rajasthan",     "302017"),
    ("CUST010", "Tirupati Transports Ltd",  "66, Vibhuti Khand, Gomti Nagar",            "Lucknow",   "Uttar Pradesh", "226010"),
]

TIERS = ["GOLD"] * 3 + ["SILVER"] * 4 + ["BRONZE"] * 3
START_DATE = "2026-01-01"
END_DATE = "2027-01-01"

MODELS = {
    "TATA":          ["Prima 4928.S", "LPT 1109", "Signa 1923.K", "Ultra 1518", "Prima 5530.S"],
    "ASHOK LEYLAND": ["Boss 1212", "Captain 3718", "AVTR 4825", "Ecomet 1015", "U-Truck 4923"],
    "EICHER":        ["Pro 6028", "Pro 3015", "Pro 8035XM", "Pro 6055T", "Pro 2049"],
    "BHARAT BENZ":   ["3128R", "1617R", "4823R", "2823R", "1015R"],
    "MAHINDRA":      ["BLAZO X 28", "BLAZO X 35", "FURIO 17", "JAYO 4019", "BLAZO X 55"],
}


def write_customers() -> None:
    with open(ROOT / "customer_master.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "customer_name", "street_address", "city", "state", "pincode"])
        w.writerows(CUSTOMERS)


def write_subscriptions() -> None:
    with open(ROOT / "subscription_master.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["subscription_id", "customer_id", "tier", "effective_start_date", "end_date"])
        for i, (cust_id, *_rest) in enumerate(CUSTOMERS):
            w.writerow([f"SUB_{i + 1}", cust_id, TIERS[i], START_DATE, END_DATE])


def write_vehicles() -> None:
    rng = random.Random(SEED)
    mfrs = list(MODELS.keys())
    with open(ROOT / "vehicle_master.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["vin", "subscription_id", "manufacturer", "model"])
        for i, (cust_id, *_rest) in enumerate(CUSTOMERS):
            sub_id = f"SUB_{i + 1}"
            for serial in range(VINS_PER_SUB):
                vin = _make_vin("V", cust_id, serial)
                mfr = rng.choice(mfrs)
                model = rng.choice(MODELS[mfr])
                w.writerow([vin, sub_id, mfr, model])


if __name__ == "__main__":
    write_customers()
    write_subscriptions()
    write_vehicles()
    print("Wrote customer_master.csv, subscription_master.csv, vehicle_master.csv")
