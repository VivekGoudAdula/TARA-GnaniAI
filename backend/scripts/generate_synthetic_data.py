"""
Generate realistic synthetic Indian customer and lead CSV datasets for TARA outreach.
Produces 200 customers and 200 leads with synthetic test phone numbers (+9190000xxxxx).
"""
from __future__ import annotations

import csv
import os
from pathlib import Path
import random

OUT_DIR = Path(__file__).parent / "out"

FIRST_NAMES = [
    "Aarav", "Aditi", "Amit", "Ananya", "Deepak", "Divya", "Karan", "Kavita",
    "Manish", "Neha", "Pooja", "Pranav", "Priya", "Rahul", "Rakesh", "Riya",
    "Rohit", "Sameer", "Sanjay", "Sneha", "Sunil", "Suresh", "Swati", "Vikas"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Rao", "Nair", "Iyer", "Mehta",
    "Chopra", "Gupta", "Joshi", "Kulkarni", "Deshmukh", "Singhania", "Bhatia"
]

CITIES = ["Mumbai", "Bengaluru", "Hyderabad", "Delhi", "Pune", "Chennai", "Kolkata", "Ahmedabad"]
LANGUAGES = ["en-IN", "hi-IN", "te-IN"]
EMPLOYMENT_TYPES = ["salaried", "salaried", "salaried", "self_employed"]


def generate_records(count: int, phone_start: int, prefix: str):
    records = []
    for i in range(count):
        fn = random.choice(FIRST_NAMES)
        ln = random.choice(LAST_NAMES)
        full_name = f"{fn} {ln}"
        phone = f"+9190000{phone_start + i:05d}"
        email = f"{fn.lower()}.{ln.lower()}{i+1}@example.com"
        age = random.randint(22, 62)
        income = round(random.uniform(22000, 185000), -2)
        emp = random.choice(EMPLOYMENT_TYPES)
        credit_score = random.randint(450, 830)
        city = random.choice(CITIES)
        lang = random.choice(LANGUAGES)

        consent = "false" if random.random() < 0.10 else "true"
        dnd = "true" if random.random() < 0.05 else "false"

        records.append({
            "external_ref": f"{prefix}_{1000 + i}",
            "full_name": full_name,
            "phone": phone,
            "email": email,
            "age": age,
            "monthly_income_inr": income,
            "employment_type": emp,
            "credit_score": credit_score,
            "city": city,
            "preferred_language": lang,
            "consent": consent,
            "dnd": dnd,
        })
    return records


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    random.seed(42)

    cust_records = generate_records(200, 1, "CUST")
    cust_file = OUT_DIR / "synthetic_customers.csv"
    with open(cust_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(cust_records[0].keys()))
        writer.writeheader()
        writer.writerows(cust_records)
    print(f"Generated 200 synthetic customers: {cust_file}")

    lead_records = generate_records(200, 201, "LEAD")
    lead_file = OUT_DIR / "synthetic_leads.csv"
    with open(lead_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(lead_records[0].keys()))
        writer.writeheader()
        writer.writerows(lead_records)
    print(f"Generated 200 synthetic leads: {lead_file}")


if __name__ == "__main__":
    main()

