
import csv
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data" / "processed"
DB_PATH = DATA_DIR / "shopwise.db"

PRODUCTS_CSV = DATA_DIR / "products.csv"
REVIEW_AUDIT_CSV = DATA_DIR / "review_text_audit.csv"


def read_csv(path):
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def to_float(value):
    if value is None or value.strip() == "":
        return None
    return float(value)


def create_database():
    products = read_csv(PRODUCTS_CSV)
    review_records = read_csv(REVIEW_AUDIT_CSV)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Rebuild this development database from the validated CSV outputs.
    # The original raw CSV is never changed.
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON")

        connection.executescript("""
            DROP TABLE IF EXISTS review_source_records;
            DROP TABLE IF EXISTS products;

            CREATE TABLE products (
                product_id TEXT PRIMARY KEY,
                product_name TEXT NOT NULL,
                category TEXT NOT NULL,
                discounted_price_inr REAL,
                actual_price_inr REAL,
                discount_percentage REAL,
                rating REAL CHECK (rating IS NULL OR rating BETWEEN 0 AND 5),
                rating_count REAL,
                about_product TEXT,
                img_link TEXT,
                product_link TEXT,
                source_row_number INTEGER,
                source_rows_for_product INTEGER NOT NULL
            );

            CREATE TABLE review_source_records (
                source_record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT NOT NULL,
                source_row_number INTEGER NOT NULL,
                review_title_raw TEXT,
                review_content_raw TEXT,
                review_content_without_urls TEXT,
                embedded_url_count INTEGER NOT NULL DEFAULT 0,
                review_boundaries_verified INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (product_id)
                    REFERENCES products(product_id)
                    ON DELETE CASCADE
            );

            CREATE INDEX idx_products_category
                ON products(category);

            CREATE INDEX idx_products_price
                ON products(discounted_price_inr);

            CREATE INDEX idx_review_source_product
                ON review_source_records(product_id);
        """)

        product_sql = """
            INSERT INTO products (
                product_id, product_name, category,
                discounted_price_inr, actual_price_inr,
                discount_percentage, rating, rating_count,
                about_product, img_link, product_link,
                source_row_number, source_rows_for_product
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        product_values = [
            (
                row["product_id"],
                row["product_name"],
                row["category"],
                to_float(row["discounted_price_inr"]),
                to_float(row["actual_price_inr"]),
                to_float(row["discount_percentage_numeric"]),
                to_float(row["rating_numeric"]),
                to_float(row["rating_count_numeric"]),
                row["about_product"],
                row["img_link"],
                row["product_link"],
                int(row["source_row_number"]),
                int(row["source_rows_for_product"]),
            )
            for row in products
        ]

        connection.executemany(product_sql, product_values)

        review_sql = """
            INSERT INTO review_source_records (
                product_id, source_row_number,
                review_title_raw, review_content_raw,
                review_content_without_urls, embedded_url_count,
                review_boundaries_verified
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """

        review_values = [
            (
                row["product_id"],
                int(row["source_row_number"]),
                row["review_title_raw"],
                row["review_content_raw"],
                row["review_content_without_urls"],
                int(row["embedded_url_count"]),
                0,  # Individual review boundaries remain unverified.
            )
            for row in review_records
        ]

        connection.executemany(review_sql, review_values)

        product_count = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        review_source_count = connection.execute(
            "SELECT COUNT(*) FROM review_source_records"
        ).fetchone()[0]

        orphan_count = connection.execute("""
            SELECT COUNT(*)
            FROM review_source_records AS r
            LEFT JOIN products AS p ON p.product_id = r.product_id
            WHERE p.product_id IS NULL
        """).fetchone()[0]

        print("\n========== DATABASE SUMMARY ==========")
        print("Database:", DB_PATH)
        print("Products loaded:", product_count)
        print("Review source records loaded:", review_source_count)
        print("Orphan review-source records:", orphan_count)

        assert product_count == len(products)
        assert review_source_count == len(review_records)
        assert orphan_count == 0

        print("\nDATABASE CHECK: PASS")


if __name__ == "__main__":
    create_database()
