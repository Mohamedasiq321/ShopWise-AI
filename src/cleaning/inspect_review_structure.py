
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "amazon.csv"
CATEGORY_PREFIX = "Computers&Accessories|"
SAMPLES_TO_SHOW = 5


def main():
    samples = []
    matching_rows = 0
    matching_product_ids = set()

    with RAW_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            category = (row.get("category") or "").strip()

            if not category.startswith(CATEGORY_PREFIX):
                continue

            matching_rows += 1
            matching_product_ids.add(row.get("product_id"))

            if len(samples) < SAMPLES_TO_SHOW:
                samples.append((row_number, row))

    print("CATEGORY VALIDATION")
    print("Matching source rows:", matching_rows)
    print("Unique product IDs:", len(matching_product_ids))

    for row_number, row in samples:
        print("\n" + "=" * 70)
        print("Source CSV row:", row_number)
        print("Product ID:", row.get("product_id"))
        print("Full category:", row.get("category"))

        for field in ("review_id", "review_title", "review_content"):
            value = row.get(field) or ""

            print(f"\n{field}")
            print("Character length:", len(value))
            print("Comma count:", value.count(","))
            print("Semicolon count:", value.count(";"))
            print("Pipe count:", value.count("|"))
            print("Newline count:", value.count("\n"))
            print("Preview:", repr(value[:500]))

    print("\nREAD-ONLY INSPECTION COMPLETE")
    print("No files were modified.")


if __name__ == "__main__":
    main()
