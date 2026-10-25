
import pandas as pd
import pytest

from src.recommendation.decision_snapshot import build_decision_snapshot


def sample_products():
    return pd.DataFrame([
        {
            "product_name": "Budget Mouse",
            "discounted_price_inr": 399,
            "rating": 4.1,
        },
        {
            "product_name": "Premium Mouse",
            "discounted_price_inr": 799,
            "rating": 4.6,
        },
        {
            "product_name": "Balanced Mouse",
            "discounted_price_inr": 599,
            "rating": 4.4,
        },
    ])


def test_snapshot_identifies_lowest_price_and_highest_rating():
    result = build_decision_snapshot(sample_products())

    assert result["lowest_price"][0]["product_name"] == "Budget Mouse"
    assert result["highest_rated"][0]["product_name"] == "Premium Mouse"
    assert "Lowest price" in result["summary"]
    assert "Highest rating" in result["summary"]


def test_snapshot_handles_ties():
    products = pd.DataFrame([
        {
            "product_name": "Mouse A",
            "discounted_price_inr": 500,
            "rating": 4.5,
        },
        {
            "product_name": "Mouse B",
            "discounted_price_inr": 500,
            "rating": 4.5,
        },
    ])

    result = build_decision_snapshot(products)

    assert len(result["lowest_price"]) == 2
    assert len(result["highest_rated"]) == 2
    assert "Mouse A" in result["summary"]
    assert "Mouse B" in result["summary"]


def test_snapshot_handles_missing_price_and_rating():
    products = pd.DataFrame([
        {
            "product_name": "Unknown Price",
            "discounted_price_inr": None,
            "rating": 4.8,
        },
        {
            "product_name": "Unknown Rating",
            "discounted_price_inr": 450,
            "rating": None,
        },
    ])

    result = build_decision_snapshot(products)

    assert result["lowest_price"][0]["product_name"] == "Unknown Rating"
    assert result["highest_rated"][0]["product_name"] == "Unknown Price"


def test_snapshot_handles_all_missing_values():
    products = pd.DataFrame([
        {
            "product_name": "Product A",
            "discounted_price_inr": None,
            "rating": None,
        },
        {
            "product_name": "Product B",
            "discounted_price_inr": float("nan"),
            "rating": float("nan"),
        },
    ])

    result = build_decision_snapshot(products)

    assert result["lowest_price"] is None
    assert result["highest_rated"] is None
    assert "unavailable" in result["summary"]


def test_snapshot_rejects_missing_required_columns():
    products = pd.DataFrame([
        {"product_name": "Product A"},
    ])

    with pytest.raises(ValueError, match="Missing required product fields"):
        build_decision_snapshot(products)
