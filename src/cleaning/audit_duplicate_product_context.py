
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"

CORPUS_CSV = DATA_DIR / "product_review_text_corpus.csv"
PRODUCTS_CSV = DATA_DIR / "products.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    corpus = read_csv(CORPUS_CSV)
    products = read_csv(PRODUCTS_CSV)

    product_lookup = {row["product_id"]: row for row in products}
    text_groups = defaultdict(list)

    for row in corpus:
        text = (row.get("review_content_without_urls") or "").strip()
        if text:
            text_groups[text].append(row["product_id"])

    duplicate_groups = [
        (text, ids)
        for text, ids in text_groups.items()
        if len(ids) > 1
    ]

    print("DUPLICATE TEXT CONTEXT AUDIT")
    print("----------------------------")
    print("Duplicate groups:", len(duplicate_groups))

    for index, (text, ids) in enumerate(duplicate_groups, start=1):
        print(f"\nGROUP {index}")
        print("Shared text length:", len(text))
        print("Product count:", len(ids))

        for product_id in ids:
            product = product_lookup.get(product_id)

            if product is None:
                print(f"- {product_id}: MISSING PRODUCT RECORD")
                continue

            print(f"- ID: {product_id}")
            print(f"  Name: {product['product_name']}")
            print(f"  Brand/category path: {product['category']}")
            print(f"  Price: {product['discounted_price']}")
            print(f"  Rating: {product['rating']}")

    print("\nREAD-ONLY AUDIT COMPLETE")
    print("No files were modified.")


if __name__ == "__main__":
    main()
