
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "amazon.csv"
CATEGORY_PREFIX = "Computers&Accessories|"


def apparent_list_count(value):
    """Count comma-separated pieces for diagnosis only."""
    if not value or not value.strip():
        return 0
    return len(value.split(","))


def main():
    rows_checked = 0
    id_title_matches = 0
    id_title_mismatches = []
    content_url_rows = 0
    content_comma_counts = Counter()
    empty_fields = Counter()

    with RAW_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        reader = csv.DictReader(file)

        for row_number, row in enumerate(reader, start=2):
            category = (row.get("category") or "").strip()
            if not category.startswith(CATEGORY_PREFIX):
                continue

            rows_checked += 1

            ids = row.get("review_id") or ""
            titles = row.get("review_title") or ""
            content = row.get("review_content") or ""

            id_count = apparent_list_count(ids)
            title_count = apparent_list_count(titles)

            if id_count == title_count:
                id_title_matches += 1
            elif len(id_title_mismatches) < 10:
                id_title_mismatches.append(
                    (row_number, row.get("product_id"),
                     id_count, title_count)
                )

            if not ids.strip():
                empty_fields["review_id"] += 1
            if not titles.strip():
                empty_fields["review_title"] += 1
            if not content.strip():
                empty_fields["review_content"] += 1

            if "http://" in content or "https://" in content:
                content_url_rows += 1

            content_comma_counts[content.count(",")] += 1

    print("REVIEW FIELD ALIGNMENT AUDIT")
    print("Source rows checked:", rows_checked)
    print("Rows where apparent ID/title counts match:",
          id_title_matches)
    print("Rows where apparent ID/title counts differ:",
          rows_checked - id_title_matches)
    print("Rows with URLs in review_content:", content_url_rows)
    print("Empty review fields:", dict(empty_fields))

    print("\nFirst apparent ID/title count mismatches:")
    for item in id_title_mismatches:
        print(
            f"CSV row {item[0]}, product {item[1]}: "
            f"IDs={item[2]}, titles={item[3]}"
        )

    print("\nMost common review_content comma counts:")
    for comma_count, frequency in content_comma_counts.most_common(10):
        print(f"{comma_count} commas: {frequency} rows")

    print("\nAUDIT COMPLETE — no files modified.")
    print("Counts are diagnostic, not proof of review boundaries.")


if __name__ == "__main__":
    main()
