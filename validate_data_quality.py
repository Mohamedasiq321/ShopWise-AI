
import csv
from collections import Counter, defaultdict
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"

def split_count(value):
    """Diagnostic only; this does NOT prove each comma marks a review boundary."""
    value = (value or "").strip()
    return len(value.split(",")) if value else 0

def main():
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    print("TOTAL ROWS:", len(rows))

    # Category-level unique product counts
    category_products = defaultdict(set)
    category_rows = Counter()

    for row in rows:
        category = (row.get("category") or "").split("|")[0].strip()
        product_id = (row.get("product_id") or "").strip()
        category_rows[category] += 1
        if product_id:
            category_products[category].add(product_id)

    print("\n=== CATEGORY COUNTS ===")
    for category, count in category_rows.most_common():
        print(
            f"{category}: {count} rows, "
            f"{len(category_products[category])} unique product IDs"
        )

    # Duplicate IDs and their conflicting fields
    by_id = defaultdict(list)
    for row in rows:
        by_id[(row.get("product_id") or "").strip()].append(row)

    duplicate_groups = [
        (product_id, group)
        for product_id, group in by_id.items()
        if product_id and len(group) > 1
    ]

    print("\n=== DUPLICATE ID SUMMARY ===")
    print("Duplicate product ID groups:", len(duplicate_groups))
    print("Rows belonging to duplicate groups:",
          sum(len(group) for _, group in duplicate_groups))
    print("Extra repeated rows:",
          sum(len(group) - 1 for _, group in duplicate_groups))

    print("\n=== FIRST 5 DUPLICATE EXAMPLES ===")
    for product_id, group in duplicate_groups[:5]:
        print("\nProduct ID:", product_id)
        for row in group:
            print({
                "name": row.get("product_name", "")[:100],
                "category": row.get("category", ""),
                "price": row.get("discounted_price", ""),
                "rating": row.get("rating", ""),
                "review_title_items": split_count(row.get("review_title")),
                "review_content_items": split_count(row.get("review_content")),
                "review_id_items": split_count(row.get("review_id")),
            })

    print("\n=== REVIEW FIELD STRUCTURE ===")
    fields = ["review_id", "user_id", "user_name",
              "review_title", "review_content"]

    for field in fields:
        counts = [split_count(row.get(field)) for row in rows]
        print(
            f"{field}: min={min(counts)}, "
            f"max={max(counts)}, "
            f"average={sum(counts) / len(counts):.2f}, "
            f"rows with multiple comma-separated parts="
            f"{sum(count > 1 for count in counts)}"
        )

    print("\nDiagnostic complete. No source data was changed.")

if __name__ == "__main__":
    main()
