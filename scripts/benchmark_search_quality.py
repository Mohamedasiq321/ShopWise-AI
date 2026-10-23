"""Evaluate ShopWise AI ranking with manually graded product relevance.

Relevance grades:
    0 = irrelevant
    1 = partially relevant
    2 = highly relevant

The product database is loaded through ProductRecommendationEngine's read-only
SQLite connection. This script writes only the evaluation report.
"""

import json
import math
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.recommendation.engine import ProductRecommendationEngine

LABELS_PATH = PROJECT_ROOT / "scripts" / "manual_relevance_labels.json"
OUTPUT_PATH = PROJECT_ROOT / "data" / "processed" / "search_quality_benchmark.json"
TOP_K = 5


def load_labels(path):
    """Load and validate manually reviewed graded relevance labels."""
    if not path.is_file():
        raise FileNotFoundError(f"Manual relevance labels not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        labels = json.load(file)

    if not isinstance(labels, dict) or not labels:
        raise ValueError("Labels must be a non-empty JSON object.")

    for query, query_labels in labels.items():
        if not isinstance(query, str) or not query.strip():
            raise ValueError("Every label entry must have a non-empty query.")
        if not isinstance(query_labels, dict) or not query_labels:
            raise ValueError(
                f"Labels for {query!r} must be a non-empty product-ID-to-grade object."
            )
        for product_id, grade in query_labels.items():
            if not isinstance(product_id, str) or not product_id.strip():
                raise ValueError(f"Invalid product ID for query {query!r}.")
            if isinstance(grade, bool) or grade not in (0, 1, 2):
                raise ValueError(
                    f"Grade for {query!r} / {product_id!r} must be 0, 1, or 2."
                )

    return labels


def dcg_at_k(grades, k):
    """Discounted cumulative gain using graded relevance and gain 2**grade - 1."""
    return sum(
        (2**grade - 1) / math.log2(rank + 1)
        for rank, grade in enumerate(grades[:k], start=1)
    )


def ndcg_at_k(result_ids, labels, k):
    """Calculate NDCG using explicitly judged relevance labels only."""
    observed_grades = [
        labels[product_id]
        for product_id in result_ids[:k]
        if product_id in labels
    ]
    ideal_grades = sorted(labels.values(), reverse=True)[:k]
    ideal_dcg = dcg_at_k(ideal_grades, k)

    if ideal_dcg == 0:
        return None

    return dcg_at_k(observed_grades, k) / ideal_dcg


def evaluate_query(engine, query, query_labels, k=TOP_K):
    labels = {str(product_id): grade for product_id, grade in query_labels.items()}

    catalogue_ids = set(engine.products["product_id"].astype(str))
    unknown_ids = set(labels) - catalogue_ids
    if unknown_ids:
        raise ValueError(
            f"Unknown product IDs for query {query!r}: {sorted(unknown_ids)}"
        )

    results = engine.search(query, limit=k)
    result_ids = results["product_id"].astype(str).tolist()

    # Only explicitly judged results count toward judged precision.
    judged_results = [
        (product_id, labels[product_id])
        for product_id in result_ids
        if product_id in labels
    ]
    judged_relevant_count = sum(grade > 0 for grade in labels.values())
    found_judged_relevant = sum(grade > 0 for _, grade in judged_results)

    judged_precision = (
        found_judged_relevant / len(judged_results)
        if judged_results else None
    )
    judged_recall = (
        found_judged_relevant / judged_relevant_count
        if judged_relevant_count else None
    )

    reciprocal_rank = 0.0
    for rank, product_id in enumerate(result_ids, start=1):
        if labels.get(product_id, 0) > 0:
            reciprocal_rank = 1.0 / rank
            break

    ndcg = ndcg_at_k(result_ids, labels, k)

    return {
        "query": query,
        "results_returned": len(results),
        "judged_products": len(labels),
        "judged_relevant_products": judged_relevant_count,
        "judged_results_returned": len(judged_results),
        "judged_precision_at_5": (
            round(judged_precision, 4)
            if judged_precision is not None else None
        ),
        "recall_at_5_among_judged_products": (
            round(judged_recall, 4) if judged_recall is not None else None
        ),
        "mrr": round(reciprocal_rank, 4),
        "ndcg_at_5": round(ndcg, 4) if ndcg is not None else None,
        "top_results": [
            {
                "product_id": str(row["product_id"]),
                "product_name": str(row["product_name"]),
                "manual_relevance_grade": labels.get(str(row["product_id"])),
                "recommendation_score": round(
                    float(row["recommendation_score"]), 6
                ),
            }
            for _, row in results.iterrows()
        ],
    }
def mean_metric(results, key):
    values = [item[key] for item in results if item[key] is not None]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def main():
    engine = ProductRecommendationEngine()
    labels = load_labels(LABELS_PATH)

    evaluations = [
        evaluate_query(engine, query, query_labels)
        for query, query_labels in labels.items()
    ]

    report = {
        "catalogue_size": len(engine.products),
        "top_k": TOP_K,
        "queries_evaluated": len(evaluations),
        "relevance_grade_guide": {
            "0": "irrelevant",
            "1": "partially relevant",
            "2": "highly relevant",
        },
        "mean_judged_precision_at_5": mean_metric(
            evaluations, "judged_precision_at_5"
        ),
        "mean_recall_at_5_among_judged_products": mean_metric(
            evaluations, "recall_at_5_among_judged_products"
        ),
        "mean_mrr": mean_metric(evaluations, "mrr"),
        "mean_ndcg_at_5": mean_metric(evaluations, "ndcg_at_5"),
        "evaluation_note": (
            "Unjudged products are excluded from judged precision and NDCG "
            "gains; they are not treated as explicitly irrelevant. Recall "
            "is limited to the manually judged set, not the full catalogue."
        ),
        "results": evaluations,
    }
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(report, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Catalogue size: {report['catalogue_size']}")
    print(f"Queries evaluated: {report['queries_evaluated']}")
    print(
    f"Mean Judged Precision@5: "
    f"{report['mean_judged_precision_at_5']}"
    )
    print(
        "Mean Recall@5 among judged products: "
        f"{report['mean_recall_at_5_among_judged_products']}"
    )
    print(f"Mean MRR: {report['mean_mrr']}")
    print(f"Mean NDCG@5: {report['mean_ndcg_at_5']}")

    for item in evaluations:
        print(f"\nQuery: {item['query']}")
        print(
            f"Returned={item['results_returned']}, "
            f"Judged Precision@5={item['judged_precision_at_5']}, "
            f"Judged Recall@5={item['recall_at_5_among_judged_products']}, "
            f"MRR={item['mrr']}, NDCG@5={item['ndcg_at_5']}"
        )
        for rank, product in enumerate(item["top_results"], start=1):
            print(
                f"  {rank}. grade={product['manual_relevance_grade']} "
                f"[{product['product_id']}] {product['product_name']}"
            )

    print(f"\nDetailed report saved to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
