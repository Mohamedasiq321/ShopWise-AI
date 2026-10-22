
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = ROOT / "data" / "raw" / "amazon.csv"
TARGET_CATEGORY = "Computers&Accessories"

def main():
    with RAW_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    grouped = defaultdict(list)

    for row in rows:
        category = (row.get("category") or "").split("|")[0].strip()
        product_id = (row.get("product_id") or "").strip()

        if category == TARGET_CATEGORY and product_id:
            grouped[product_id].append(row)

    found = 0

    for product_id, group in grouped.items():
        descriptions = list(dict.fromkeys(
            row.get("about_product", "").strip()
            for row in group
        ))

        if len(descriptions) > 1:
            found += 1
            print(f"\n{'=' * 60}")
            print("Product ID:", product_id)
            print("Rows:", len(group))
            for i, description in enumerate(descriptions, start=1):
                print(f"\nDescription {i}:\n{description[:900]}")

    print(f"\nConflicting description groups inspected: {found}")
    print("Original dataset was not modified.")

if __name__ == "__main__":
    main()
