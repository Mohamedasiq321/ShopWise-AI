
import csv
import re
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"
TARGET_CATEGORY = "Computers&Accessories"

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)

def parse_inr(value):
    if not value:
        return None

    cleaned = value.replace("₹", "").replace(",", "").strip()

    try:
        return float(cleaned)
    except ValueError:
        return None

def main():
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    category_rows = [
        row for row in rows
        if (row.get("category") or "").split("|")[0].strip()
        == TARGET_CATEGORY
    ]

    # Keep this diagnostic conservative: one representative row per product.
    # We are measuring coverage, not yet resolving conflicting duplicate records.
    unique_rows = {}
    for row in category_rows:
        product_id = (row.get("product_id") or "").strip()
        if product_id and product_id not in unique_rows:
            unique_rows[product_id] = row

    products = list(unique_rows.values())
    valid_discounted = sum(
        parse_inr(row.get("discounted_price")) is not None
        for row in products
    )
    valid_actual = sum(
        parse_inr(row.get("actual_price")) is not None
        for row in products
    )
    valid_rating = sum(
        parse_inr(row.get("rating")) is not None
        and 0 <= parse_inr(row.get("rating")) <= 5
        for row in products
    )
    valid_description = sum(
        bool((row.get("about_product") or "").strip())
        for row in products
    )
    review_urls = sum(
        bool(URL_PATTERN.search(row.get("review_content") or ""))
        for row in products
    )
    review_text = sum(
        bool(URL_PATTERN.sub("", row.get("review_content") or "").strip())
        for row in products
    )

    print("CATEGORY:", TARGET_CATEGORY)
    print("Source rows:", len(category_rows))
    print("Unique product IDs:", len(products))
    print("Valid discounted prices:", valid_discounted)
    print("Valid actual prices:", valid_actual)
    print("Valid 0-5 ratings:", valid_rating)
    print("Products with descriptions:", valid_description)
    print("Products with URLs in review_content:", review_urls)
    print("Products with remaining review text after URL removal:", review_text)
    print("\nNo source data was modified.")

if __name__ == "__main__":
    main()
