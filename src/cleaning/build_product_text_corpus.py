
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

PRODUCTS_CSV = DATA_DIR / "products.csv"
REVIEW_AUDIT_CSV = DATA_DIR / "review_text_audit.csv"
OUTPUT_CSV = DATA_DIR / "product_review_text_corpus.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    if OUTPUT_CSV.exists():
        raise FileExistsError(
            f"Output already exists; refusing to overwrite it:\n{OUTPUT_CSV}"
        )

    products = read_csv(PRODUCTS_CSV)
    review_rows = read_csv(REVIEW_AUDIT_CSV)

    # Match the exact source row selected by the cleaning pipeline.
    selected_sources = {
        (
            row["product_id"].strip(),
            row["source_row_number"].strip(),
        ): row
        for row in review_rows
    }

    if len(selected_sources) != len(review_rows):
        raise ValueError(
            "Duplicate product_id/source_row_number pairs in review audit."
        )

    corpus = []
    seen_product_ids = set()
    missing_matches = []

    for product in products:
        product_id = product["product_id"].strip()
        source_row_number = product["source_row_number"].strip()

        if product_id in seen_product_ids:
            raise ValueError(f"Duplicate product ID: {product_id}")

        seen_product_ids.add(product_id)

        key = (product_id, source_row_number)
        source = selected_sources.get(key)

        if source is None:
            missing_matches.append(key)
            continue

        raw_content = source.get("review_content_raw") or ""
        cleaned_content = source.get("review_content_without_urls") or ""

        corpus.append({
            "product_id": product_id,
            "product_name": product["product_name"],
            "source_row_number": source_row_number,
            "review_title_raw": source.get("review_title_raw") or "",
            "review_content_raw": raw_content,
            "review_content_without_urls": cleaned_content,
            "embedded_url_count": source.get("embedded_url_count") or "0",
            "review_boundaries_verified": "false",
            "text_character_count": str(len(cleaned_content)),
        })

    if missing_matches:
        raise ValueError(
            f"Could not match {len(missing_matches)} selected source rows. "
            f"Examples: {missing_matches[:5]}"
        )

    if len(corpus) != len(products):
        raise ValueError(
            f"Expected {len(products)} corpus rows, got {len(corpus)}."
        )

    fieldnames = [
        "product_id",
        "product_name",
        "source_row_number",
        "review_title_raw",
        "review_content_raw",
        "review_content_without_urls",
        "embedded_url_count",
        "review_boundaries_verified",
        "text_character_count",
    ]

    with OUTPUT_CSV.open(
        "x", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(corpus)

    print("PRODUCT-LEVEL TEXT CORPUS CREATED")
    print("Output:", OUTPUT_CSV)
    print("Products:", len(products))
    print("Corpus rows:", len(corpus))
    print("Unique product IDs:", len(seen_product_ids))
    print("Missing source-row matches:", len(missing_matches))
    print(
        "Rows marked with unverified review boundaries:",
        sum(row["review_boundaries_verified"] == "false"
            for row in corpus),
    )
    print(
        "Rows with empty cleaned content:",
        sum(not row["review_content_without_urls"].strip()
            for row in corpus),
    )
    print("\nOriginal data and database were not modified.")


if __name__ == "__main__":
    main()
