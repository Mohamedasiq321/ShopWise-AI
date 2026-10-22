
import csv
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH = Path(__file__).parent / "data" / "raw" / "amazon.csv"

def main():
    with DATA_PATH.open("r", encoding="utf-8-sig", newline="") as file:
        rows = list(csv.DictReader(file))

    affected = []
    for row in rows:
        content = row.get("review_content", "")
        if "http://" in content or "https://" in content:
            affected.append(row)

    print("Total source rows:", len(rows))
    print("Rows with URLs inside review_content:", len(affected))

    print("\nFirst 5 affected rows:")
    for row in affected[:5]:
        content = row.get("review_content", "")
        urls = [
            part.strip()
            for part in content.split(",")
            if "http://" in part or "https://" in part
        ]
        print("\nProduct ID:", row.get("product_id"))
        print("Product name:", row.get("product_name", "")[:100])
        print("URL-like segments:", len(urls))
        for url in urls[:3]:
            print(" ", url[:160])

    print("\nInspection only. Original CSV unchanged.")

if __name__ == "__main__":
    main()
