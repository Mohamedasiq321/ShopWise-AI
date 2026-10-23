
from src.recommendation.engine import ProductRecommendationEngine
from src.recommendation.query_intent import detect_query_intent


def test_supported_product_intents_are_detected():
    cases = {
        "Bluetooth speaker": "bluetooth_speaker",
        "soundbar": "soundbar",
        "wireless earbuds": "wireless_earbuds",
        "TWS earbuds": "wireless_earbuds",
        "gaming mouse": "gaming_mouse",
        "USB-C cable": "usb_c_cable",
        "webcam": "webcam",
        "external hard drive": "external_hard_drive",
        "wireless keyboard": "wireless_keyboard",
    }

    for query, expected_type in cases.items():
        assert detect_query_intent(query).product_type == expected_type


def test_gaming_mouse_search_returns_relevant_products():
    engine = ProductRecommendationEngine()
    results = engine.search("gaming mouse", limit=5)

    assert len(results) >= 3
    for name in results["product_name"].str.lower():
        assert "gaming" in name
        assert "mouse" in name
        assert "mousepad" not in name
        assert "mouse pad" not in name


def test_usb_c_cable_search_returns_relevant_products():
    engine = ProductRecommendationEngine()
    results = engine.search("USB-C cable", limit=5)

    assert len(results) >= 3

    for name in results["product_name"].str.lower():
        assert "cable" in name
        assert (
            "type-c" in name
            or "type c" in name
            or "usb-c" in name
            or "usb c" in name
        )
        assert "lightning" not in name



def test_wireless_keyboard_search_returns_relevant_products():
    engine = ProductRecommendationEngine()
    results = engine.search("wireless keyboard", limit=5)

    assert len(results) >= 2

    for name in results["product_name"].str.lower():
        assert "keyboard" in name
        assert "wireless" in name or "bluetooth" in name
        assert "mouse" not in name


def test_bluetooth_speaker_search_never_returns_unrelated_products():
    engine = ProductRecommendationEngine()
    results = engine.search("Bluetooth speaker", limit=10)

    for name in results["product_name"].str.lower():
        assert "bluetooth" in name
        assert "speaker" in name
        assert "adapter" not in name
        assert "dongle" not in name


def test_soundbar_search_never_returns_unrelated_products():
    engine = ProductRecommendationEngine()
    results = engine.search("soundbar", limit=10)

    for name in results["product_name"].str.lower():
        assert "soundbar" in name or "sound bar" in name


def test_wireless_earbuds_search_returns_only_earbud_products():
    engine = ProductRecommendationEngine()
    results = engine.search("wireless earbuds", limit=10)

    for name in results["product_name"].str.lower():
        assert "earbud" in name


def test_search_results_are_sorted_by_recommendation_score():
    engine = ProductRecommendationEngine()

    for query in (
        "gaming mouse",
        "USB-C cable",
        "wireless keyboard",
    ):
        results = engine.search(query, limit=5)

        scores = results["recommendation_score"].tolist()
        assert scores == sorted(scores, reverse=True)


def test_audio_search_respects_budget():
    engine = ProductRecommendationEngine()
    budget = 5000

    results = engine.search(
        "wireless earbuds",
        max_budget=budget,
        limit=10,
    )

    assert (results["discounted_price_inr"] <= budget).all()


def test_empty_catalogue_matches_return_empty_results():
    engine = ProductRecommendationEngine()

    # These categories currently have no verified title matches
    # in the existing 375-product catalogue.
    for query in ("Bluetooth speaker", "soundbar"):
        results = engine.search(query, limit=5)
        assert results.empty


def test_wireless_keyboard_combo_intent_is_detected():
    assert (
        detect_query_intent("wireless keyboard and mouse combo").product_type
        == "wireless_keyboard_combo"
    )


def test_standalone_wireless_keyboard_search_excludes_combo_sets():
    engine = ProductRecommendationEngine()
    results = engine.search("wireless keyboard", limit=10)

    for name in results["product_name"].str.lower():
        assert "keyboard" in name
        assert not (
            "mouse" in name
            and any(term in name for term in ("combo", "set", "keyboard and mouse"))
        )

def test_wireless_keyboard_combo_search_returns_combo_products():
    engine = ProductRecommendationEngine()
    results = engine.search("wireless keyboard and mouse combo", limit=10)

    assert not results.empty

    for name in results["product_name"].str.lower():
        assert "keyboard" in name
        assert "mouse" in name


def test_wireless_keyboard_combo_search_excludes_wired_products():
    engine = ProductRecommendationEngine()
    results = engine.search(
        "wireless keyboard and mouse combo",
        limit=10,
    )

    assert not results.empty

    for name in results["product_name"].str.lower():
        assert "keyboard" in name
        assert "mouse" in name
        assert "wired" not in name
        assert any(
            term in name
            for term in ("wireless", "bluetooth", "2.4ghz", "2.4 ghz")
        )


def test_mouse_search_excludes_mousepads_and_combo_sets():
    engine = ProductRecommendationEngine()
    results = engine.search("mouse", limit=10)

    assert not results.empty
    leaves = results["category"].fillna("").str.split("|").str[-1]
    assert leaves.isin(["Mice", "GamingMice"]).all()


def test_mousepad_search_returns_mousepad_category():
    engine = ProductRecommendationEngine()
    results = engine.search("mousepad", limit=10)

    assert not results.empty
    leaves = results["category"].fillna("").str.split("|").str[-1]
    assert leaves.eq("MousePads").all()


def test_headphones_search_excludes_unrelated_mouse_products():
    engine = ProductRecommendationEngine()
    results = engine.search("headphones", limit=10)

    assert not results.empty
    leaves = results["category"].fillna("").str.split("|").str[-1]
    assert leaves.str.contains("Headsets", case=False).all()


def test_laptop_search_prioritizes_actual_laptop_category():
    engine = ProductRecommendationEngine()
    results = engine.search("laptop", limit=10)

    assert not results.empty
    leaves = results["category"].fillna("").str.split("|").str[-1]
    assert leaves.eq("TraditionalLaptops").all()
