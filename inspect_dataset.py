
import csv
from collections import Counter
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"

REQUIRED_COLUMNS = [
    "product_id",
    "product_name",
    "category",
    "discounted_price",
    "actual_price",
    "rating",
    "rating_count",
    "about_product",
    "review_title",
    "review_content",
]

def main():
    if not DATA_PATH.exists():
        print(f"ERROR: Dataset not found at:\n{DATA_PATH}")
        print("Check the filename and folder structure.")
        return

    print(f"Dataset: {DATA_PATH}")
    print(f"File size: {DATA_PATH.stat().st_size / (1024 * 1024):.2f} MB")

    try:
        with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            columns = reader.fieldnames or []
            missing_columns = [
                column for column in REQUIRED_COLUMNS
                if column not in columns
            ]

            print(f"\nColumns found: {len(columns)}")
            print("Columns:", columns)

            if missing_columns:
                print("\nMissing required columns:", missing_columns)
                return

            total_rows = 0
            product_ids = set()
            duplicate_ids = 0
            category_counts = Counter()
            missing_counts = Counter()
            review_text_rows = 0
            description_rows = 0
            sample_products = []

            for row in reader:
                total_rows += 1

                product_id = (row.get("product_id") or "").strip()

                if product_id:
                    if product_id in product_ids:
                        duplicate_ids += 1
                    product_ids.add(product_id)

                category = (row.get("category") or "").strip()
                main_category = (
                    category.split("|")[0].strip()
                    if category else "Missing category"
                )
                category_counts[main_category] += 1

                for column in REQUIRED_COLUMNS:
                    if not (row.get(column) or "").strip():
                        missing_counts[column] += 1

                if (row.get("review_content") or "").strip():
                    review_text_rows += 1

                if (row.get("about_product") or "").strip():
                    description_rows += 1

                if (
                    main_category == "Computers&Accessories"
                    and len(sample_products) < 3
                ):
                    sample_products.append({
                        "name": row.get("product_name", ""),
                        "price": row.get("discounted_price", ""),
                        "rating": row.get("rating", ""),
                        "review": (row.get("review_content") or "")[:180],
                    })

    except (OSError, csv.Error, UnicodeError) as error:
        print(f"\nERROR reading dataset: {error}")
        return

    print("\n========== DATASET SUMMARY ==========")
    print("Total rows:", total_rows)
    print("Distinct non-empty product IDs:", len(product_ids))
    print("Duplicate product ID rows:", duplicate_ids)
    print("Rows with review text:", review_text_rows)
    print("Rows with product descriptions:", description_rows)

    print("\n========== CATEGORY COUNTS ==========")
    for category, count in category_counts.most_common(12):
        print(f"{category}: {count}")

    print("\n========== MISSING VALUES ==========")
    for column in REQUIRED_COLUMNS:
        print(f"{column}: {missing_counts[column]}")

    print("\n========== SAMPLE PRODUCTS ==========")
    for product in sample_products:
        print("\nName:", product["name"])
        print("Price:", product["price"])
        print("Rating:", product["rating"])
        print("Review preview:", product["review"])

    print("\nInspection completed. The original CSV was not modified.")

if __name__ == "__main__":
    main()
