
"""Offline baseline evaluation for ShopWise AI recommendations."""

from src.recommendation.engine import ProductRecommendationEngine


QUERIES = [
    "wireless mouse",
    "gaming mouse",
    "USB-C cable",
    "wireless keyboard",
    "webcam",
    "laptop stand",
    "Bluetooth speaker",
    "external hard drive",
]

BUDGETS = {
    "wireless mouse": 1000,
    "gaming mouse": 2000,
    "USB-C cable": 500,
    "wireless keyboard": 2000,
    "webcam": 3000,
    "laptop stand": 1500,
    "Bluetooth speaker": 2000,
    "external hard drive": 5000,
}


def main():
    engine = ProductRecommendationEngine()

    print("=" * 88)
    print("SHOPWISE AI — BASELINE RECOMMENDATION EVALUATION")
    print("=" * 88)
    print(f"Products available: {len(engine.products)}")
    print("Note: this is a diagnostic benchmark, not a formal relevance score.")

    for query in QUERIES:
        budget = BUDGETS[query]
        results = engine.search(
            query=query,
            max_budget=budget,
            limit=5,
        )

        print("\n" + "-" * 88)
        print(f"QUERY: {query!r} | MAXIMUM BUDGET: Rs. {budget}")
        print("-" * 88)

        if results.empty:
            print("NO RESULTS")
            continue

        within_budget = (
            results["discounted_price_inr"].notna()
            & (results["discounted_price_inr"] <= budget)
        ).all()

        print("Budget constraint passed:", within_budget)

        for rank, (_, product) in enumerate(results.iterrows(), start=1):
            name = str(product["product_name"]).replace("\n", " ")
            name = name[:150] + ("..." if len(name) > 150 else "")

            print(
                f"{rank}. {name}\n"
                f"   ID: {product['product_id']} | "
                f"Price: Rs. {product['discounted_price_inr']:.2f} | "
                f"Rating: {product['rating']} | "
                f"Relevance: {product['relevance_score']:.4f} | "
                f"Score: {product['recommendation_score']:.4f}"
            )

        if not within_budget:
            print("WARNING: At least one returned product violates the budget.")

    print("\n" + "=" * 88)
    print("EVALUATION COMPLETE")
    print("Review product relevance manually before changing ranking weights.")
    print("=" * 88)


if __name__ == "__main__":
    main()
