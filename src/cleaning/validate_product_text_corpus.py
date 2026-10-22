
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

PRODUCTS_CSV = DATA_DIR / "products.csv"
REVIEW_AUDIT_CSV = DATA_DIR / "review_text_audit.csv"
CORPUS_CSV = DATA_DIR / "product_review_text_corpus.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    products = read_csv(PRODUCTS_CSV)
    audit = read_csv(REVIEW_AUDIT_CSV)
    corpus = read_csv(CORPUS_CSV)

    products_by_id = {r["product_id"]: r for r in products}
    audit_by_source = {
        (r["product_id"], r["source_row_number"]): r
        for r in audit
    }

    corpus_ids = [r["product_id"] for r in corpus]

    checks = {}

    checks["Corpus contains 375 rows"] = len(corpus) == 375
    checks["Corpus product IDs are unique"] = (
        len(corpus_ids) == len(set(corpus_ids))
    )
    checks["All corpus products exist in products.csv"] = all(
        product_id in products_by_id for product_id in corpus_ids
    )

    checks["Selected source rows match products.csv"] = all(
        row["source_row_number"]
        == products_by_id[row["product_id"]]["source_row_number"]
        for row in corpus
        if row["product_id"] in products_by_id
    )

    raw_text_matches = True
    cleaned_counts_match = True
    boundaries_unverified = True
    source_matches_exist = True

    for row in corpus:
        key = (row["product_id"], row["source_row_number"])
        source = audit_by_source.get(key)

        if source is None:
            source_matches_exist = False
            continue

        if row["review_content_raw"] != source["review_content_raw"]:
            raw_text_matches = False

        cleaned_text = row["review_content_without_urls"]
        if len(cleaned_text) != int(row["text_character_count"]):
            cleaned_counts_match = False

        if row["review_boundaries_verified"].lower() != "false":
            boundaries_unverified = False

    checks["Every corpus row matches a source audit row"] = (
        source_matches_exist
    )
    checks["Raw content matches source audit exactly"] = raw_text_matches
    checks["Cleaned text character counts are correct"] = cleaned_counts_match
    checks["All review boundaries remain marked unverified"] = (
        boundaries_unverified
    )

    print("PRODUCT TEXT CORPUS VALIDATION")
    print("------------------------------")
    for description, passed in checks.items():
        print(f"{'PASS' if passed else 'FAIL'}: {description}")

    failed = [name for name, passed in checks.items() if not passed]
    print("\nOVERALL CHECK:", "PASS" if not failed else "FAIL")

    if failed:
        raise SystemExit(
            "Validation failed. Do not continue to sentiment analysis."
        )

    print("No files were modified.")


if __name__ == "__main__":
    main()
