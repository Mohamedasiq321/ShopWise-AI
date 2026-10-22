
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "processed" / "shopwise.db"

EXPECTED_PRODUCTS = 375
EXPECTED_REVIEW_RECORDS = 453


def verify_database():
    if not DB_PATH.is_file():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")

    # Open the database in read-only mode.
    uri = DB_PATH.resolve().as_uri() + "?mode=ro"

    with sqlite3.connect(uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only = ON")

        tables = {
            row["name"]
            for row in connection.execute("""
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
            """)
        }

        required_tables = {"products", "review_source_records"}
        missing_tables = required_tables - tables
        assert not missing_tables, f"Missing tables: {missing_tables}"

        products = connection.execute(
            "SELECT COUNT(*) FROM products"
        ).fetchone()[0]

        reviews = connection.execute(
            "SELECT COUNT(*) FROM review_source_records"
        ).fetchone()[0]

        null_required = connection.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE product_id IS NULL
               OR TRIM(product_id) = ''
               OR product_name IS NULL
               OR TRIM(product_name) = ''
               OR category IS NULL
               OR TRIM(category) = ''
        """).fetchone()[0]

        invalid_prices = connection.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE discounted_price_inr IS NULL
               OR discounted_price_inr <= 0
               OR actual_price_inr IS NULL
               OR actual_price_inr <= 0
        """).fetchone()[0]

        invalid_ratings = connection.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE rating IS NOT NULL
              AND (rating < 0 OR rating > 5)
        """).fetchone()[0]

        duplicate_ids = connection.execute("""
            SELECT COUNT(*) FROM (
                SELECT product_id
                FROM products
                GROUP BY product_id
                HAVING COUNT(*) > 1
            )
        """).fetchone()[0]

        orphan_reviews = connection.execute("""
            SELECT COUNT(*)
            FROM review_source_records AS r
            LEFT JOIN products AS p ON p.product_id = r.product_id
            WHERE p.product_id IS NULL
        """).fetchone()[0]

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()

        stats = connection.execute("""
            SELECT MIN(discounted_price_inr) AS min_price,
                   MAX(discounted_price_inr) AS max_price,
                   MIN(rating) AS min_rating,
                   MAX(rating) AS max_rating
            FROM products
        """).fetchone()

        print("\n========== SHOPWISE DATABASE VALIDATION ==========")
        print("Database:", DB_PATH)
        print(f"Products: {products} (expected {EXPECTED_PRODUCTS})")
        print(
            f"Review-source records: {reviews} "
            f"(expected {EXPECTED_REVIEW_RECORDS})"
        )
        print("Rows missing required product fields:", null_required)
        print("Rows with missing/invalid prices:", invalid_prices)
        print("Rows with out-of-range ratings:", invalid_ratings)
        print("Duplicate product IDs:", duplicate_ids)
        print("Orphan review-source records:", orphan_reviews)
        print("Foreign-key violations:", len(foreign_key_errors))
        print(
            f"Price range: ₹{stats['min_price']:.2f} "
            f"to ₹{stats['max_price']:.2f}"
        )
        print(
            f"Rating range: {stats['min_rating']} "
            f"to {stats['max_rating']}"
        )

        assert products == EXPECTED_PRODUCTS, "Unexpected product count"
        assert reviews == EXPECTED_REVIEW_RECORDS, "Unexpected review count"
        assert null_required == 0, "Required product fields are missing"
        assert invalid_prices == 0, "Missing or invalid prices found"
        assert invalid_ratings == 0, "Ratings outside 0–5 found"
        assert duplicate_ids == 0, "Duplicate product IDs found"
        assert orphan_reviews == 0, "Orphan review-source records found"
        assert not foreign_key_errors, "Foreign-key violations found"
        assert stats["min_price"] is not None, "No valid prices found"
        assert stats["min_rating"] is not None, "No ratings found"

        print("\nDATABASE VALIDATION: PASS")
        print("Database opened read-only; no data was modified.")


if __name__ == "__main__":
    verify_database()
