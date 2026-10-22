
import csv
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CORPUS_CSV = ROOT / "data" / "processed" / "product_review_text_corpus.csv"

HTML_PATTERN = re.compile(r"<[^>]+>")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)


def main():
    with CORPUS_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        rows = list(csv.DictReader(file))

    text_groups = defaultdict(list)
    html_rows = []
    long_rows = []

    for row in rows:
        text = (row.get("review_content_without_urls") or "").strip()
        product_id = row["product_id"]
        product_name = row["product_name"]

        if text:
            # Exact text comparison; no records are merged or deleted.
            text_groups[text].append((product_id, product_name))

        if HTML_PATTERN.search(text):
            html_rows.append((row, text))

        if len(text) > 5000:
            long_rows.append((row, text))

    duplicate_groups = [
        (text, products)
        for text, products in text_groups.items()
        if len(products) > 1
    ]

    print("TEXT ANOMALY INVESTIGATION")
    print("--------------------------")
    print("Corpus rows:", len(rows))
    print("Exact duplicate text groups:", len(duplicate_groups))
    print("Rows with HTML-like markup:", len(html_rows))
    print("Rows longer than 5,000 characters:", len(long_rows))
    print("Rows with URLs still detected:", sum(
        bool(URL_PATTERN.search(
            row.get("review_content_without_urls") or ""
        ))
        for row in rows
    ))

    print("\nHTML-LIKE MARKUP RECORDS")
    for row, text in html_rows[:5]:
        print(f"\nProduct: {row['product_id']} | {row['product_name'][:80]}")
        for match in HTML_PATTERN.finditer(text):
            print("Markup:", repr(match.group(0)))
        print("Text preview:", repr(text[:500]))

    print("\nEXACT DUPLICATE TEXT GROUPS — FIRST 10")
    for text, products in duplicate_groups[:10]:
        print("\nText preview:", repr(text[:180]))
        for product_id, product_name in products:
            print(f"- {product_id}: {product_name[:80]}")

    print("\nLONG TEXT RECORDS — FIRST 10")
    for row, text in sorted(
        long_rows, key=lambda item: len(item[1]), reverse=True
    )[:10]:
        print(
            f"- {row['product_id']} | "
            f"{len(text)} characters | "
            f"{row['product_name'][:80]}"
        )
        print("  Preview:", repr(text[:250]))

    print("\nREAD-ONLY INVESTIGATION COMPLETE")
    print("No files were modified.")


if __name__ == "__main__":
    main()
