
import csv
from collections import defaultdict
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"

PRODUCT_FIELDS = [
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
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    grouped = defaultdict(list)

    for row in rows:
        product_id = (row.get("product_id") or "").strip()
        if product_id:
            grouped[product_id].append(row)

    duplicate_groups = {
        product_id: group
        for product_id, group in grouped.items()
        if len(group) > 1
    }

    identical_groups = 0
    conflicting_groups = 0
    review_field_differences = 0

    for product_id, group in duplicate_groups.items():
        first = group[0]

        product_details_match = all(
            all(row.get(field) == first.get(field) for field in PRODUCT_FIELDS)
            for row in group[1:]
        )

        reviews_match = all(
            all(
                row.get(field) == first.get(field)
                for field in [
                    "review_id",
                    "user_id",
                    "user_name",
                    "review_title",
                    "review_content",
                ]
            )
            for row in group[1:]
        )

        if product_details_match and reviews_match:
            identical_groups += 1
        else:
            conflicting_groups += 1

        if not reviews_match:
            review_field_differences += 1

    print("Duplicate product ID groups:", len(duplicate_groups))
    print("Groups with fully identical product and review fields:", identical_groups)
    print("Groups with conflicting fields:", conflicting_groups)
    print("Groups with differing review fields:", review_field_differences)

    print("\nFirst 5 duplicate groups:")
    for product_id, group in list(duplicate_groups.items())[:5]:
        print(f"\n{product_id}: {len(group)} rows")
        for field in ["product_name", "discounted_price", "rating",
                      "review_id", "review_title", "review_content"]:
            values = {row.get(field, "") for row in group}
            print(f"  {field}: {len(values)} distinct value(s)")

    print("\nNo records were changed.")

if __name__ == "__main__":
    main()
