
import pytest

from src.recommendation.engine import ProductRecommendationEngine


@pytest.fixture(scope="module")
def engine():
    return ProductRecommendationEngine()


def test_database_loads_unique_products(engine):
    assert len(engine.products) == 375
    assert engine.products["product_id"].is_unique


def test_search_returns_results(engine):
    results = engine.search("wireless mouse", limit=5)

    assert not results.empty
    assert len(results) <= 5
    assert results["product_id"].is_unique
    assert results["relevance_score"].between(0, 1).all()


def test_budget_is_respected(engine):
    budget = 1000
    results = engine.search(
        "mouse", max_budget=budget, limit=20
    )

    assert (
        results["discounted_price_inr"] <= budget
    ).all()


def test_minimum_rating_is_respected(engine):
    minimum = 4.0
    results = engine.search(
        "mouse", min_rating=minimum, limit=20
    )

    assert (results["rating"] >= minimum).all()


def test_blank_query_returns_top_rated_products(engine):
    results = engine.search("", limit=5)

    assert len(results) == 5
    assert results["rating"].is_monotonic_decreasing


def test_comparison_returns_requested_products(engine):
    results = engine.search("wireless mouse", limit=2)
    product_ids = results["product_id"].tolist()

    comparison = engine.compare(product_ids)

    assert comparison["product_id"].tolist() == product_ids
    assert len(comparison) == 2


def test_alternatives_exclude_original_product(engine):
    product_id = engine.search(
        "wireless mouse", limit=1
    ).iloc[0]["product_id"]

    alternatives = engine.alternatives(product_id, limit=5)

    assert product_id not in alternatives["product_id"].tolist()
    assert alternatives["product_id"].is_unique


@pytest.mark.parametrize("budget", [0, -100, "invalid", True])
def test_invalid_budgets_are_rejected(engine, budget):
    with pytest.raises(ValueError):
        engine.search("mouse", max_budget=budget)


def test_unknown_product_comparison_is_rejected(engine):
    with pytest.raises(ValueError):
        engine.compare(["FAKE_PRODUCT_1", "FAKE_PRODUCT_2"])


def test_unknown_alternative_source_is_rejected(engine):
    with pytest.raises(ValueError):
        engine.alternatives("FAKE_PRODUCT", limit=5)


def test_gaming_mouse_search_excludes_headphones_and_earbuds(engine):
    results = engine.search("gaming mouse", max_budget=2000, limit=10)

    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "gaming" in name
        assert "mouse" in name or "mice" in name
        assert "headphone" not in name
        assert "earbud" not in name


def test_usb_c_cable_results_have_title_evidence(engine):
    results = engine.search("USB-C cable", max_budget=500, limit=10)
def test_usb_c_cable_search_excludes_lightning_cables(engine):
    results = engine.search("USB-C cable", max_budget=500, limit=10)

    assert not results.empty
    assert not results["product_name"].str.contains(
        r"\blightning\b", case=False, regex=True, na=False
    ).any()
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "cable" in name
        assert (
            "usb-c" in name
            or "usb c" in name
            or "usb type-c" in name
            or "type-c" in name
            or "type c" in name
        )


def test_webcam_search_excludes_privacy_accessories(engine):
    results = engine.search("webcam", max_budget=3000, limit=10)

    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "webcam" in name or "web camera" in name
        assert not any(
            term in name
            for term in ("cover", "privacy", "protector", "blocker")
        )


def test_bluetooth_speaker_search_does_not_return_unrelated_products(engine):
    results = engine.search("Bluetooth speaker", max_budget=2000, limit=10)

    for name in results["product_name"].str.lower():
        assert "bluetooth" in name
        assert "speaker" in name
        assert "adapter" not in name
        assert "dongle" not in name


def test_external_hard_drive_search_excludes_accessories(engine):
    results = engine.search(
        "external hard drive", max_budget=5000, limit=10
    )

    assert not results.empty
    for name in results["product_name"].str.lower():
        assert (
            "hard drive" in name
            or "hard disk drive" in name
            or "hdd" in name
        )
        assert "portable" in name or "external" in name
        assert not any(
            term in name for term in ("cable", "case", "caddy", "cover", "adapter")
        )

def test_query_search_excludes_products_with_zero_text_relevance(engine):
    results = engine.search("wireless mouse", limit=10)

    assert not results.empty
    assert (results["relevance_score"] > 0).all()