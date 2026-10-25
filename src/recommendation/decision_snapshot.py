
import math

import pandas as pd


def _valid_number(value):
    """Return True for finite numeric values, excluding booleans."""
    if value is None or isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False


def build_decision_snapshot(products):
    """
    Summarize price and rating trade-offs for selected products.

    Returns a dictionary containing the cheapest product, highest-rated
    product, and a factual comparison summary. Missing values are ignored.
    """
    if not isinstance(products, pd.DataFrame):
        raise TypeError("products must be a pandas DataFrame.")

    if products.empty:
        raise ValueError("Select at least two products to compare.")

    required_columns = {
        "product_name",
        "discounted_price_inr",
        "rating",
    }
    missing_columns = required_columns - set(products.columns)

    if missing_columns:
        raise ValueError(
            "Missing required product fields: "
            + ", ".join(sorted(missing_columns))
        )

    records = products.to_dict(orient="records")

    for record in records:
        record["product_name"] = (
            str(record.get("product_name") or "Unnamed product")
        )

    priced = [
        record
        for record in records
        if _valid_number(record.get("discounted_price_inr"))
        and float(record["discounted_price_inr"]) >= 0
    ]

    rated = [
        record
        for record in records
        if _valid_number(record.get("rating"))
        and 0 <= float(record["rating"]) <= 5
    ]

    cheapest = None
    if priced:
        lowest_price = min(
            float(record["discounted_price_inr"])
            for record in priced
        )
        cheapest = [
            record for record in priced
            if float(record["discounted_price_inr"]) == lowest_price
        ]

    highest_rated = None
    if rated:
        highest_rating = max(
            float(record["rating"]) for record in rated
        )
        highest_rated = [
            record for record in rated
            if float(record["rating"]) == highest_rating
        ]

    summary_parts = []

    if cheapest:
        names = ", ".join(item["product_name"] for item in cheapest)
        summary_parts.append(
            f"Lowest price: {names} at INR "
            f"{float(cheapest[0]['discounted_price_inr']):,.2f}."
        )
    else:
        summary_parts.append("Price comparison is unavailable.")

    if highest_rated:
        names = ", ".join(
            item["product_name"] for item in highest_rated
        )
        summary_parts.append(
            f"Highest rating: {names} at "
            f"{float(highest_rated[0]['rating']):.1f}/5."
        )
    else:
        summary_parts.append("Rating comparison is unavailable.")

    if cheapest and highest_rated:
        cheapest_ids = {id(item) for item in cheapest}
        highest_ids = {id(item) for item in highest_rated}

        if cheapest_ids & highest_ids:
            summary_parts.append(
                "At least one product leads on both price and rating."
            )
        else:
            summary_parts.append(
                "The lowest-price and highest-rated options differ; "
                "choose based on whether price or rating matters more."
            )

    return {
        "lowest_price": cheapest,
        "highest_rated": highest_rated,
        "summary": " ".join(summary_parts),
    }
