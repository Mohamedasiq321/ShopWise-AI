
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
CORPUS_CSV = DATA_DIR / "product_review_text_corpus.csv"
OUTPUT_CSV = DATA_DIR / "text_anomaly_report.csv"

LONG_TEXT_THRESHOLD = 5000
PREVIEW_LENGTH = 350


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def main():
    if OUTPUT_CSV.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing report: {OUTPUT_CSV}"
        )

    rows = read_csv(CORPUS_CSV)
    text_groups = defaultdict(list)
    report = []

    for row in rows:
        text = (row.get("review_content_without_urls") or "").strip()
        text_groups[text].append(row)

    # Report all products whose text exceeds the threshold.
    for row in rows:
        text = (row.get("review_content_without_urls") or "").strip()

        if len(text) > LONG_TEXT_THRESHOLD:
            report.append({
                "anomaly_type": "long_text",
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "text_length": len(text),
                "group_size": 1,
                "related_product_ids": row["product_id"],
                "preview": text[:PREVIEW_LENGTH],
            })

    # Report exact duplicate text groups without removing any data.
    duplicate_groups = [
        group for text, group in text_groups.items()
        if text and len(group) > 1
    ]

    for group in duplicate_groups:
        text = (group[0].get("review_content_without_urls") or "").strip()

        report.append({
            "anomaly_type": "duplicate_text",
            "product_id": group[0]["product_id"],
            "product_name": group[0]["product_name"],
            "text_length": len(text),
            "group_size": len(group),
            "related_product_ids": ";".join(
                row["product_id"] for row in group
            ),
            "preview": text[:PREVIEW_LENGTH],
        })

    fields = [
        "anomaly_type",
        "product_id",
        "product_name",
        "text_length",
        "group_size",
        "related_product_ids",
        "preview",
    ]

    with OUTPUT_CSV.open(
        "x", encoding="utf-8-sig", newline=""
    ) as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(report)

    print("TEXT ANOMALY REPORT CREATED")
    print("Corpus rows:", len(rows))
    print("Long-text records:", sum(
        item["anomaly_type"] == "long_text" for item in report
    ))
    print("Duplicate-text groups:", len(duplicate_groups))
    print("Report rows:", len(report))
    print("Report path:", OUTPUT_CSV)
    print("Original corpus and database were not modified.")

    print("\nLONG-TEXT RECORDS")
    for item in report:
        if item["anomaly_type"] == "long_text":
            print(
                f"- {item['product_id']} | "
                f"{item['text_length']} characters | "
                f"{item['product_name'][:65]}"
            )
            print("  Preview:", repr(item["preview"]))

    print("\nDUPLICATE GROUP SUMMARY")
    for index, group in enumerate(duplicate_groups, start=1):
        text = (group[0].get("review_content_without_urls") or "").strip()
        print(
            f"- Group {index}: {len(group)} products, "
            f"{len(text)} characters"
        )
        print("  Product IDs:", ", ".join(
            row["product_id"] for row in group
        ))


if __name__ == "__main__":
    main()
