
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

def read_csv(filename):
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))

def main():
    products = read_csv("products.csv")
    conflicts = read_csv("product_conflict_audit.csv")
    descriptions = read_csv("description_variants_audit.csv")
    reviews = read_csv("review_text_audit.csv")

    ids = [row["product_id"] for row in products]
    id_set = set(ids)

    duplicate_ids = len(ids) - len(id_set)
    missing_ids = sum(not value.strip() for value in ids)

    invalid_prices = 0
    invalid_ratings = 0

    for row in products:
        try:
            price = float(row["discounted_price_inr"])
            if price < 0:
                invalid_prices += 1
        except (ValueError, TypeError):
            invalid_prices += 1

        try:
            rating = float(row["rating_numeric"])
            if not 0 <= rating <= 5:
                invalid_ratings += 1
        except (ValueError, TypeError):
            invalid_ratings += 1

    unknown_conflict_ids = sum(
        row["product_id"] not in id_set for row in conflicts
    )
    unknown_description_ids = sum(
        row["product_id"] not in id_set for row in descriptions
    )
    unknown_review_ids = sum(
        row["product_id"] not in id_set for row in reviews
    )

    print("========== CLEANED DATA VALIDATION ==========")
    print("Products:", len(products))
    print("Unique product IDs:", len(id_set))
    print("Duplicate product IDs:", duplicate_ids)
    print("Missing product IDs:", missing_ids)
    print("Invalid discounted prices:", invalid_prices)
    print("Invalid ratings:", invalid_ratings)
    print("Conflict audit rows:", len(conflicts))
    print("Description variant rows:", len(descriptions))
    print("Review source audit rows:", len(reviews))
    print("Unknown IDs in conflict audit:", unknown_conflict_ids)
    print("Unknown IDs in description audit:", unknown_description_ids)
    print("Unknown IDs in review audit:", unknown_review_ids)

    passed = (
        len(products) >= 50
        and duplicate_ids == 0
        and missing_ids == 0
        and invalid_prices == 0
        and invalid_ratings == 0
        and unknown_conflict_ids == 0
        and unknown_description_ids == 0
        and unknown_review_ids == 0
    )

    print("\nOVERALL CHECK:", "PASS" if passed else "FAIL")
    print("Note: review boundaries are not validated by this script.")

if __name__ == "__main__":
    main()
