
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "processed" / "shopwise.db"


def verify_database():
    with sqlite3.connect(DB_PATH) as connection:
        connection.row_factory = sqlite3.Row

        # Test 1: Retrieve a few products
        products = connection.execute("""
            SELECT product_id, product_name,
                   discounted_price_inr, rating
            FROM products
            LIMIT 5
        """).fetchall()

        print("\nTEST 1: Sample products")
        for product in products:
            print(
                f"- {product['product_name'][:65]} | "
                f"₹{product['discounted_price_inr']:.2f} | "
                f"Rating: {product['rating']}"
            )

        # Test 2: Retrieve products within a ₹1,000 budget
        budget_products = connection.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE discounted_price_inr <= ?
        """, (1000,)).fetchone()[0]

        print("\nTEST 2: Products priced at ₹1,000 or less")
        print("Matching products:", budget_products)

        # Test 3: Retrieve highly rated products
        highly_rated = connection.execute("""
            SELECT COUNT(*)
            FROM products
            WHERE rating >= ?
        """, (4.0,)).fetchone()[0]

        print("\nTEST 3: Products rated 4.0 or higher")
        print("Matching products:", highly_rated)

        # Test 4: Check price and rating ranges
        stats = connection.execute("""
            SELECT MIN(discounted_price_inr) AS min_price,
                   MAX(discounted_price_inr) AS max_price,
                   MIN(rating) AS min_rating,
                   MAX(rating) AS max_rating
            FROM products
        """).fetchone()

        print("\nTEST 4: Data ranges")
        print(f"Price range: ₹{stats['min_price']:.2f} "
              f"to ₹{stats['max_price']:.2f}")
        print(f"Rating range: {stats['min_rating']} "
              f"to {stats['max_rating']}")

        assert len(products) == 5
        assert budget_products >= 0
        assert highly_rated >= 0
        assert stats["min_price"] > 0
        assert 0 <= stats["min_rating"] <= 5
        assert 0 <= stats["max_rating"] <= 5

        print("\nDATABASE QUERY CHECK: PASS")


if __name__ == "__main__":
    verify_database()
