
import csv
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT / "data" / "raw" / "amazon.csv"
TARGET_CATEGORY = "Computers&Accessories"

FIELDS = [
    "product_name",
    "category",
    "discounted_price",
    "actual_price",
    "discount_percentage",
    "rating",
    "rating_count",
    "about_product",
    "img_link",
    "product_link",
]

def main():
    with RAW_FILE.open("r", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    groups = defaultdict(list)

    for row in rows:
        category = (row.get("category") or "").split("|")[0].strip()
        product_id = (row.get("product_id") or "").strip()

        if category == TARGET_CATEGORY and product_id:
            groups[product_id].append(row)

    conflicts = Counter()
    conflicting_groups = 0

    for product_id, group in groups.items():
        fields_that_differ = [
            field for field in FIELDS
            if len({row.get(field, "").strip() for row in group}) > 1
        ]

        if fields_that_differ:
            conflicting_groups += 1
            conflicts.update(fields_that_differ)

    print("Unique product IDs:", len(groups))
    print("Groups with conflicting product fields:", conflicting_groups)
    print("\nConflicts by field:")

    for field, count in conflicts.most_common():
        print(f"{field}: {count} product groups")

    print("\nNo source data was modified.")

if __name__ == "__main__":
    main()
