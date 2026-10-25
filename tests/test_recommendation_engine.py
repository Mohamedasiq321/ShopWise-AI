import re
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
    results = engine.search("mouse", max_budget=1000, limit=20)
    assert (results["discounted_price_inr"] <= 1000).all()


def test_minimum_rating_is_respected(engine):
    results = engine.search("mouse", min_rating=4.0, limit=20)
    assert (results["rating"] >= 4.0).all()


def test_blank_query_returns_top_rated_products(engine):
    results = engine.search("", limit=5)
    assert len(results) == 5
    assert results["rating"].is_monotonic_decreasing


def test_comparison_returns_requested_products(engine):
    ids = engine.search("wireless mouse", limit=2)["product_id"].tolist()
    comparison = engine.compare(ids)
    assert comparison["product_id"].tolist() == ids


def test_alternatives_exclude_original_product(engine):
    product_id = engine.search("wireless mouse", limit=1).iloc[0]["product_id"]
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


def test_gaming_mouse_search_excludes_unrelated_products(engine):
    results = engine.search("gaming mouse", max_budget=2000, limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "gaming" in name and "mouse" in name
        assert not any(term in name for term in ("mousepad", "mouse pad", "headphone", "earbud"))


def test_usb_c_cable_results_have_title_evidence(engine):
    results = engine.search("USB-C cable", max_budget=500, limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "cable" in name
        assert any(term in name for term in ("usb-c", "usb c", "type-c", "type c"))


def test_usb_c_cable_search_excludes_lightning_cables(engine):
    results = engine.search("USB-C cable", max_budget=500, limit=10)
    assert not results["product_name"].str.contains(
        r"\blightning\b", case=False, regex=True, na=False
    ).any()


def test_webcam_search_excludes_privacy_accessories(engine):
    results = engine.search("webcam", max_budget=3000, limit=20)

    accessory_patterns = (
        r"\bwebcam\s+cover\b",
        r"\bweb\s+camera\s+cover\b",
        r"\bcamera\s+privacy\s+covers?\b",
        r"\bprivacy\s+covers?\b",
        r"\bwebcam\s+(?:protector|blocker)\b",
        r"\bcover\s+slide\b",
    )

    for name in results["product_name"].str.lower():
        assert "webcam" in name or "web camera" in name
        assert not any(
            re.search(pattern, name)
            for pattern in accessory_patterns
        )


def test_bluetooth_speaker_search_does_not_return_unrelated_products(engine):
    results = engine.search("Bluetooth speaker", max_budget=2000, limit=10)
    for name in results["product_name"].str.lower():
        assert "bluetooth" in name and "speaker" in name
        assert "adapter" not in name and "dongle" not in name


def test_external_hard_drive_search_excludes_accessories(engine):
    results = engine.search("external hard drive", max_budget=5000, limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert any(term in name for term in ("hard drive", "hard disk drive", "hdd"))
        assert "portable" in name or "external" in name
        assert not any(term in name for term in ("cable", "case", "caddy", "cover", "adapter"))


def test_query_search_excludes_products_with_zero_text_relevance(engine):
    results = engine.search("wireless mouse", limit=10)
    assert not results.empty
    assert (results["relevance_score"] > 0).all()


def test_wireless_keyboard_search_returns_keyboard_products(engine):
    results = engine.search("wireless keyboard", limit=10)
    assert not results.empty
    assert all("keyboard" in name.lower() for name in results["product_name"])


def test_wireless_keyboard_search_excludes_keyboard_accessories(engine):
    results = engine.search("wireless keyboard", limit=10)
    assert not results["product_name"].str.contains(
        r"keyboard cover|keyboard case|keycap",
        case=False, regex=True, na=False,
    ).any()


@pytest.mark.parametrize("query", ["mouse", "wireless mouse"])
def test_mouse_search_excludes_mousepads_and_combos(engine, query):
    results = engine.search(query, limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "mouse" in name or "mice" in name
        assert not any(term in name for term in ("mousepad", "mouse pad", "mouse mat"))
        assert not ("keyboard" in name and any(term in name for term in ("combo", "set")))


def test_mousepad_search_returns_mousepad_products(engine):
    results = engine.search("mousepad", limit=10)
    assert not results.empty
    assert all(
        any(term in name.lower() for term in ("mousepad", "mouse pad", "mouse mat"))
        for name in results["product_name"]
    )


def test_laptop_sleeve_search_returns_sleeves(engine):
    results = engine.search("laptop sleeve", limit=10)
    assert not results.empty
    assert all("sleeve" in name.lower() or "slipcase" in name.lower()
               for name in results["product_name"])


def test_headphones_search_excludes_mouse_products(engine):
    results = engine.search("headphones", limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert not any(term in name for term in ("mouse", "mousepad", "mouse pad"))


def test_charger_search_returns_charging_products(engine):
    results = engine.search("charger", limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert any(term in name for term in ("charger", "charging", "power supply", "power cable"))


def test_laptop_search_returns_actual_laptop_category(engine):
    results = engine.search("laptop", limit=10)
    assert not results.empty
    assert all("laptop" in category.lower() or "traditionallaptop" in category.lower()
               for category in results["category"])


def test_wireless_keyboard_combo_search_returns_combo_products(engine):
    results = engine.search("wireless keyboard combo", limit=10)
    assert not results.empty
    for name in results["product_name"].str.lower():
        assert "keyboard" in name and "mouse" in name
        assert any(term in name for term in ("combo", "set", "keyboard and mouse", "keyboard & mouse"))
        assert any(term in name for term in ("wireless", "bluetooth", "2.4ghz", "2.4 ghz"))
        assert "wired" not in name

def test_wireless_keyboard_alternatives_exclude_wired_keyboards_and_combos(engine):
    results = engine.search("wireless keyboard", limit=10)
    assert not results.empty

    source = results.iloc[0]
    alternatives = engine.alternatives(source["product_id"], limit=10)

    for _, product in alternatives.iterrows():
        name = product["product_name"].lower()
        category = product["category"].lower()

        assert "keyboard" in name
        assert "wireless" in name or "bluetooth" in name
        assert "keyboard&mousesets" not in category
        assert "keyboard and mouse" not in name
        assert "keyboard & mouse" not in name
        assert "combo" not in name


def test_webcam_alternatives_exclude_privacy_covers(engine):
    results = engine.search("webcam", limit=10)
    assert not results.empty

    source = results.iloc[0]
    alternatives = engine.alternatives(source["product_id"], limit=10)

    for _, product in alternatives.iterrows():
        name = product["product_name"].lower()
        category = product["category"].lower()

        assert "webcam" in name or "web camera" in name
        assert "camera privacy covers" not in category
        assert not any(
            term in name
            for term in ("webcam cover", "privacy protector", "cover slide")
        )

def test_webcam_with_builtin_privacy_shutter_is_not_an_accessory(engine):
    products = engine.products[
        engine.products["product_name"].str.contains(
            "Lenovo 300 FHD Webcam",
            case=False,
            regex=False,
            na=False,
        )
    ]

    assert len(products) == 1
    assert engine._alternative_family(products.iloc[0]) == "webcam"

def test_webcam_with_builtin_privacy_shutter_is_searchable(engine):
    results = engine.search("webcam", max_budget=3000, limit=20)

    assert results["product_name"].str.contains(
        "Lenovo 300 FHD Webcam",
        case=False,
        regex=False,
        na=False,
    ).any()
def test_review_only_term_retrieves_product_with_matching_review(engine):
    from sklearn.metrics.pairwise import cosine_similarity

    analyzer = engine.vectorizer.build_analyzer()

    product_tokens = set()
    for text in engine.products["search_text"].fillna("").astype(str):
        product_tokens.update(analyzer(text))

    review_tokens = set()
    for text in engine.products["review_text"].fillna("").astype(str):
        review_tokens.update(analyzer(text))

    candidates = sorted(
        token
        for token in review_tokens - product_tokens
        if len(token) >= 5 and token.isalpha()
    )

    for term in candidates:
        query_vector = engine.vectorizer.transform([term])
        if query_vector.nnz == 0:
            continue

        matching_products = engine.products[
            engine.products["review_text"].apply(
                lambda text: term in analyzer(str(text))
            )
        ]

        for _, product in matching_products.iterrows():
            product_id = str(product["product_id"])
            results = engine.search(term, limit=len(engine.products))

            if results.empty or product_id not in results["product_id"].astype(str).values:
                continue

            product_position = engine.products.index[
                engine.products["product_id"].astype(str) == product_id
            ][0]

            review_score = cosine_similarity(
                query_vector,
                engine.review_matrix[product_position],
            )[0, 0]

            if review_score > 0:
                assert product_id in results["product_id"].astype(str).values
                return

    raise AssertionError(
        "Could not find a review-only term that retrieves its associated product."
    )
