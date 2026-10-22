
import csv
from pathlib import Path

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"
TARGET_ID = "B07JW9H4J1"

def main():
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    matches = [
        row for row in rows
        if row.get("product_id", "").strip() == TARGET_ID
    ]

    print("Product ID:", TARGET_ID)
    print("Matching rows:", len(matches))

    for index, row in enumerate(matches, start=1):
        print(f"\n{'=' * 20} ROW {index} {'=' * 20}")

        for field in [
            "product_name",
            "discounted_price",
            "rating",
            "rating_count",
            "review_id",
            "review_title",
            "review_content",
        ]:
            value = row.get(field, "")
            print(f"\n{field}:\n{value}\n")

    print("\nInspection only: no source records were modified.")

if __name__ == "__main__":
    main()
