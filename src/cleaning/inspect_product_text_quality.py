
import csv
import re
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[2]
CORPUS_CSV = ROOT / "data" / "processed" / "product_review_text_corpus.csv"

URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
HTML_PATTERN = re.compile(r"<[^>]+>")


def read_corpus():
    with CORPUS_CSV.open(
        "r", encoding="utf-8-sig", newline=""
    ) as file:
        return list(csv.DictReader(file))


def percentile(sorted_values, fraction):
    if not sorted_values:
        return 0
    index = round((len(sorted_values) - 1) * fraction)
    return sorted_values[index]


def main():
    rows = read_corpus()

    if not rows:
        raise ValueError("Corpus is empty.")

    lengths = []
    word_counts = []
    empty_count = 0
    short_count = 0
    remaining_url_count = 0
    html_like_count = 0
    duplicate_texts = {}

    for row in rows:
        text = row.get("review_content_without_urls") or ""
        text = text.strip()

        char_count = len(text)
        word_count = len(text.split())

        lengths.append(char_count)
        word_counts.append(word_count)

        if not text:
            empty_count += 1
        if char_count < 50:
            short_count += 1
        if URL_PATTERN.search(text):
            remaining_url_count += 1
        if HTML_PATTERN.search(text):
            html_like_count += 1

        if text:
            duplicate_texts.setdefault(text, []).append(row["product_id"])

    sorted_lengths = sorted(lengths)
    sorted_words = sorted(word_counts)

    duplicate_groups = [
        product_ids
        for product_ids in duplicate_texts.values()
        if len(product_ids) > 1
    ]

    print("PRODUCT TEXT QUALITY PROFILE")
    print("----------------------------")
    print("Corpus rows:", len(rows))
    print("Empty text rows:", empty_count)
    print("Rows with fewer than 50 characters:", short_count)
    print("Rows with remaining URLs:", remaining_url_count)
    print("Rows with HTML-like tags:", html_like_count)
    print("Duplicate non-empty text groups:", len(duplicate_groups))

    print("\nCharacter count statistics")
    print("Minimum:", min(sorted_lengths))
    print("Median:", median(sorted_lengths))
    print("90th percentile:", percentile(sorted_lengths, 0.90))
    print("Maximum:", max(sorted_lengths))

    print("\nWord count statistics")
    print("Minimum:", min(sorted_words))
    print("Median:", median(sorted_words))
    print("90th percentile:", percentile(sorted_words, 0.90))
    print("Maximum:", max(sorted_words))

    print("\nFive shortest text samples")
    for row in sorted(
        rows,
        key=lambda r: len(
            (r.get("review_content_without_urls") or "").strip()
        ),
    )[:5]:
        text = row.get("review_content_without_urls") or ""
        print(
            f"- {row['product_id']}: "
            f"{len(text.strip())} characters | {text[:180]!r}"
        )

    print("\nFive longest text samples")
    for row in sorted(
        rows,
        key=lambda r: len(
            (r.get("review_content_without_urls") or "").strip()
        ),
        reverse=True,
    )[:5]:
        text = row.get("review_content_without_urls") or ""
        print(
            f"- {row['product_id']}: "
            f"{len(text.strip())} characters | {text[:180]!r}"
        )

    print("\nREAD-ONLY INSPECTION COMPLETE")
    print("No files were modified.")


if __name__ == "__main__":
    main()
