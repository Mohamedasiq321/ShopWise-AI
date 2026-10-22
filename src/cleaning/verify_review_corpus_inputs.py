
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

PRODUCTS_CSV = DATA_DIR / "products.csv"
REVIEW_AUDIT_CSV = DATA_DIR / "review_text_audit.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    products = read_csv(PRODUCTS_CSV)
    review_rows = read_csv(REVIEW_AUDIT_CSV)

    product_ids = [row["product_id"].strip() for row in products]
    product_id_set = set(product_ids)
    review_product_ids = [
        row["product_id"].strip() for row in review_rows
    ]

    review_counts = Counter(review_product_ids)

    missing_ids = [
        product_id for product_id in review_product_ids
        if product_id not in product_id_set
    ]

    products_without_reviews = [
        product_id for product_id in product_id_set
        if review_counts[product_id] == 0
    ]

    products_with_multiple_source_rows = {
        product_id: count
        for product_id, count in review_counts.items()
        if count > 1
    }

    print("REVIEW CORPUS INPUT CHECK")
    print("-------------------------")
    print("Product rows:", len(products))
    print("Unique product IDs:", len(product_id_set))
    print("Review audit rows:", len(review_rows))
    print("Unique product IDs in review audit:", len(review_counts))
    print("Review audit rows with unknown product IDs:", len(missing_ids))
    print("Products without review audit rows:", len(products_without_reviews))
    print(
        "Products with multiple review source rows:",
        len(products_with_multiple_source_rows),
    )

    print("\nReview source-row count distribution:")
    for count, frequency in sorted(
        Counter(review_counts.values()).items()
    ):
        print(f"{count} source row(s): {frequency} product(s)")

    if missing_ids:
        print("\nFirst unknown product IDs:", missing_ids[:10])

    if products_without_reviews:
        print(
            "\nFirst products without review records:",
            products_without_reviews[:10],
        )

    print("\nCHECKS")
    checks = {
        "Product IDs are unique": len(product_ids) == len(product_id_set),
        "Every review audit product exists in products.csv": not missing_ids,
        "Every selected product has review source data": not products_without_reviews,
        "Review audit has expected source rows": len(review_rows) == 453,
        "Products file has expected rows": len(products) == 375,
    }

    for description, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {description}")

    print("\nNo files were modified.")


if __name__ == "__main__":
    main()
