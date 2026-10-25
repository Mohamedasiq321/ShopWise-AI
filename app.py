"""ShopWise AI: product discovery, comparison, and alternatives."""

import math

import streamlit as st
import urllib.error
import urllib.request

from src.recommendation.engine import ProductRecommendationEngine
from src.recommendation.decision_snapshot import build_decision_snapshot


st.set_page_config(
    page_title="ShopWise AI | Smart Shopping",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_engine():
    """Create and cache the recommendation engine."""
    return ProductRecommendationEngine()



import re


def is_valid_number(value):
    """Return True for finite numeric values, excluding NaN and infinity."""
    if value is None or isinstance(value, bool):
        return False

    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError, OverflowError):
        return False

def get_review_insights(review_text, query="", max_insights=3):
    """Extract short, query-relevant excerpts from stored review text."""
    if not isinstance(review_text, str) or not review_text.strip():
        return []

    # The source data may concatenate review records, so avoid
    # presenting fragments as independently verified reviews.
    text = re.sub(r"\s+", " ", review_text).strip()
    segments = re.split(r"(?<=[.!?])\s+", text)

    query_terms = {
        term.lower()
        for term in re.findall(r"[a-zA-Z0-9]+", query)
        if len(term) >= 3
    }

    candidates = []
    seen = set()

    for segment in segments:
        segment = segment.strip(" ,;|")
        if len(segment) < 20:
            continue

        normalized = segment.lower()
        if normalized in seen:
            continue
        seen.add(normalized)

        terms = set(re.findall(r"[a-zA-Z0-9]+", normalized))
        overlap = len(query_terms & terms)

        if query_terms and overlap == 0:
            continue

        excerpt = segment[:240].rstrip()
        if len(segment) > 240:
            excerpt += "..."

        candidates.append((overlap, excerpt))

    candidates.sort(key=lambda item: item[0], reverse=True)

    return [
        excerpt
        for _, excerpt in candidates[:max_insights]
    ]

    if value is None or isinstance(value, bool):
        return False
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number)


def product_label(name, product_id, max_length=85):
    """Create a readable, unique product label for selection widgets."""
    text = str(name or "Product").strip()
    if len(text) > max_length:
        text = text[: max_length - 1].rstrip() + "..."
    return f"{text} | ID: {product_id}"

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_product_image(url):
    """Fetch and cache an image; return None if it cannot be loaded."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return None

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ShopWiseAI/1.0"},
    )

    try:
        with urllib.request.urlopen(request, timeout=3) as response:
            content_type = response.headers.get("Content-Type", "")
            if not content_type.lower().startswith("image/"):
                return None

            data = response.read(5 * 1024 * 1024 + 1)
            if len(data) > 5 * 1024 * 1024:
                return None

            if data:
                return data

    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return None

    return None


engine = load_engine()

st.title("ShopWise AI")
st.caption(
    "Find products, compare options, and explore alternatives "
    "using transparent, data-driven recommendations."
)

with st.expander("What can you shop for?", expanded=False):
    st.markdown(
        "ShopWise AI currently focuses on **computers and accessories**."
    )
    st.caption(
        "Try mice, keyboards, mousepads, USB cables, laptop sleeves, "
        "chargers, webcams, or storage devices."
    )
    st.caption(
        "Clothing, shoes, and other unsupported categories may not be "
        "available in the current catalogue."
    )

with st.sidebar:
    st.header("Shopping preferences")

    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. wireless mouse, USB-C cable",
    )

    max_budget = st.number_input(
        "Maximum budget (INR)",
        min_value=0,
        max_value=100000,
        value=0,
        step=100,
        help="Enter 0 for no budget limit.",
    )

    min_rating = st.slider(
        "Minimum customer rating",
        min_value=0.0,
        max_value=5.0,
        value=0.0,
        step=0.5,
    )

    result_limit = st.selectbox(
        "Number of results",
        options=[5, 10, 15, 20],
        index=1,
    )

    search_clicked = st.button(
        "Find products",
        type="primary",
        use_container_width=True,
    )

# Keep search results available when the user switches tabs.
if "shopwise_results" not in st.session_state:
    st.session_state.shopwise_results = None

if "shopwise_query" not in st.session_state:
    st.session_state.shopwise_query = ""

if search_clicked:
    try:
        found_results = engine.search(
            query=query.strip(),
            max_budget=max_budget if max_budget > 0 else None,
            min_rating=min_rating if min_rating > 0 else None,
            limit=result_limit,
        )
        st.session_state.shopwise_results = found_results
        st.session_state.shopwise_query = query.strip()
    except (ValueError, RuntimeError) as exc:
        st.error(f"Unable to search products: {exc}")

results = st.session_state.shopwise_results

tab_discover, tab_compare, tab_alternatives = st.tabs(
    ["Discover", "Compare", "Alternatives"]
)

with tab_discover:
    st.subheader("Product discovery")

    if results is None:
        st.info(
            "Enter a product or feature in the sidebar and select "
            "**Find products**. Leave the query blank to browse products."
        )

    elif results.empty:
        st.warning("No matching products found.")
        st.markdown(
            "**Try one of these searches:** "
            "`wireless mouse`, `keyboard`, `USB-C cable`, "
            "`laptop sleeve`, or `webcam`."
        )
        st.caption(
            "You can also increase your budget, lower the minimum rating, "
            "or clear your search to browse available products."
        )

    else:
        st.write(f"Showing **{len(results)}** matching products.")

        for _, product in results.iterrows():
            with st.container(border=True):
                left, right = st.columns([4, 1])

                with left:
                    raw_name = product.get("product_name", "Product")
                    name = str(raw_name) if raw_name is not None else "Product"
                    if len(name) > 100:
                        name = name[:97].rstrip() + "..."
                    st.markdown(f"### {name}")

                    price = product.get("discounted_price_inr")
                    actual_price = product.get("actual_price_inr")
                    rating = product.get("rating")
                    discount = product.get("discount_percentage")

                    if is_valid_number(price):
                        st.markdown(f"**Price: INR {float(price):,.0f}**")
                    else:
                        st.markdown("**Price: Not available**")

                    metrics = []
                    if is_valid_number(rating):
                        metrics.append(f"Rating: {float(rating):.1f}/5")
                    if is_valid_number(discount) and float(discount) > 0:
                        metrics.append(f"{float(discount):.0f}% off")
                    if metrics:
                        st.caption(" | ".join(metrics))

                    if (
                        is_valid_number(actual_price)
                        and is_valid_number(price)
                        and float(actual_price) > float(price)
                    ):
                        savings = float(actual_price) - float(price)
                        st.caption(f"You save: INR {savings:,.0f}")

                    description = product.get("about_product")
                    if isinstance(description, str) and description.strip():
                        with st.expander("Product details"):
                            st.write(description)


                    review_text = product.get("review_text", "")
                    search_query = st.session_state.get("shopwise_query", "")

                    review_insights = get_review_insights(
                        review_text,
                        query=search_query,
                    )

                    if review_insights:
                        with st.expander("Review insights"):
                            st.caption(
                                "Relevant excerpts from the available review text. "
                                "These are not verified individual reviews."
                            )
                            for insight in review_insights:
                                st.write(f"• {insight}")
                    else:
                        st.caption("No relevant review excerpts found for this search.")

                    explanation = product.get("explanation")
                    if explanation:
                        st.caption(str(explanation))

                    product_url = product.get("product_link")
                    if (
                        isinstance(product_url, str)
                        and product_url.startswith("https://")
                    ):
                        st.markdown(
                            f"[View product on seller's page]({product_url})"
                        )

                with right:

                    score = product.get("recommendation_score")
                    if is_valid_number(score):
                        st.metric(
                            "Rec. score",
                            f"{float(score):.3f}",
                            help=(
                                "Weighted ranking score, not a probability. With a search "
                                "query: 75% search relevance and 25% normalized rating. "
                                "Without a query: normalized rating alone. Higher scores "
                                "rank more favorably within this recommendation system."
                            ),
                        )

                    image_url = product.get("img_link")
                    image_data = fetch_product_image(image_url)

                    if image_data:
                        st.image(
                            image_data,
                            use_container_width=True,
                        )
                    else:
                        st.caption("Image unavailable")

with tab_compare:
    st.subheader("Compare products")

    if results is None or results.empty:
        st.info("Search for products first, then select products to compare.")
    else:
        available = {}
        for row in results.itertuples(index=False):
            label = product_label(row.product_name, row.product_id)
            available[label] = row.product_id

        selected_labels = st.multiselect(
            "Select two or three products",
            options=list(available.keys()),
            max_selections=3,
            key="shopwise_compare_selection",
        )

        if st.button("Compare selected", key="compare_button"):
            selected_ids = [available[label] for label in selected_labels]

            if len(selected_ids) < 2:
                st.warning("Please select at least two products.")
            else:
                try:
                    comparison = engine.compare(selected_ids)


                    # ShopWise Decision Snapshot
                    snapshot = build_decision_snapshot(comparison)

                    def _display_product_name(name, limit=48):
                        """Create a compact display name without changing source data."""
                        name = str(name or "Unnamed product")
                        name = name.split("|")[0].strip()
                        if len(name) > limit:
                            return name[: limit - 3].rstrip() + "..."
                        return name

                    st.markdown("### ShopWise Decision Snapshot")
                    st.caption(
                        "Compare the essentials first. Explore the full specifications below."
                    )

                    cheapest = snapshot["lowest_price"]
                    highest_rated = snapshot["highest_rated"]

                    # Product highlights
                    price_col, rating_col = st.columns(2, gap="medium")

                    with price_col:
                        with st.container(border=True):
                            st.markdown("**LOWEST PRICE**")

                            if cheapest:
                                for product in cheapest:
                                    st.markdown(
                                        f"**{_display_product_name(product['product_name'])}**"
                                    )
                                    st.metric(
                                        label="Current price",
                                        value=(
                                            f"₹{float(product['discounted_price_inr']):,.0f}"
                                        ),
                                    )
                                st.caption("Best for shoppers prioritizing price.")
                            else:
                                st.caption("Price information unavailable.")

                    with rating_col:
                        with st.container(border=True):
                            st.markdown("**HIGHEST RATED**")

                            if highest_rated:
                                for product in highest_rated:
                                    st.markdown(
                                        f"**{_display_product_name(product['product_name'])}**"
                                    )
                                    st.metric(
                                        label="Customer rating",
                                        value=f"{float(product['rating']):.1f} / 5",
                                    )
                                st.caption("Highest listed rating among your selections.")
                            else:
                                st.caption("Rating information unavailable.")


                    # Concise, tie-aware buying guidance
                    if cheapest and highest_rated:

                        def _product_key(product):
                            product_id = product.get("product_id")
                            if product_id is not None and str(product_id).strip():
                                return ("id", str(product_id).strip())

                            return (
                                "name",
                                str(product.get("product_name") or "").strip(),
                            )

                        cheapest_keys = {
                            _product_key(product) for product in cheapest
                        }
                        highest_keys = {
                            _product_key(product) for product in highest_rated
                        }

                        shared_leaders = cheapest_keys & highest_keys

                        if shared_leaders:
                            if len(cheapest) == 1 and len(highest_rated) == 1:
                                st.success(
                                    "The same product has both the lowest "
                                    "price and the highest listed rating."
                                )
                            else:
                                st.success(
                                    "At least one product shares both the "
                                    "lowest-price and highest-rating positions."
                                )
                        else:
                            st.info(
                                "The lowest-price and highest-rated products "
                                "differ. Compare their specifications and "
                                "decide whether the price difference is worth it."
                            )

                    elif cheapest:
                        st.info(
                            "A lowest-price option is available, but there "
                            "isn't enough valid rating data to identify a "
                            "highest-rated option."
                        )

                    elif highest_rated:
                        st.info(
                            "A highest-rated option is available, but there "
                            "isn't enough valid price data to identify a "
                            "lowest-price option."
                        )

                    else:
                        st.info(
                            "There isn't enough valid price or rating data "
                            "to identify either leader."
                        )

                    st.divider()


                    fields = {
                        "Product": "product_name",
                        "Price (INR)": "discounted_price_inr",
                        "Actual price (INR)": "actual_price_inr",
                        "Rating (/5)": "rating",
                        "Discount (%)": "discount_percentage",
                        "Description": "about_product",
                    }

                    available_fields = {
                        label: column
                        for label, column in fields.items()
                        if column in comparison.columns
                    }

                    table = comparison[
                        list(available_fields.values())
                    ].rename(
                        columns={
                            column: label
                            for label, column in available_fields.items()
                        }
                    )

                    if "Product" in table.columns:
                        table["Product"] = table["Product"].apply(
                            lambda name: _display_product_name(name, limit=36)
                        )
                        table = table.set_index("Product").T

                    st.dataframe(
                        table.astype(str),
                        use_container_width=True,
                        height=320,
                    )

                except (ValueError, KeyError, RuntimeError) as exc:
                    st.error(f"Unable to compare products: {exc}")

with tab_alternatives:
    st.subheader("Find alternatives")

    if results is None or results.empty:
        st.info("Search for a product first to explore similar alternatives.")
    else:
        choices = {}
        for row in results.itertuples(index=False):
            label = product_label(row.product_name, row.product_id)
            choices[label] = row.product_id

        selected_label = st.selectbox(
            "Choose a product",
            options=list(choices.keys()),
            key="shopwise_alternative_source",
        )

        alternative_budget = st.number_input(
            "Alternative budget limit (INR)",
            min_value=0,
            max_value=100000,
            value=0,
            step=100,
            help="Enter 0 for no budget limit.",
            key="shopwise_alternative_budget",
        )

        if st.button("Find alternatives", key="alternatives_button"):
            try:
                alternatives = engine.alternatives(
                    choices[selected_label],
                    max_budget=(
                        alternative_budget
                        if alternative_budget > 0
                        else None
                    ),
                    limit=5,
                )

                if alternatives.empty:
                    st.warning(
                        "No similar alternatives found under those constraints."
                    )
                else:

                    # ShopWise Alternative Insights
                    source_rows = results[
                        results["product_id"].astype(str)
                        == str(choices[selected_label])
                    ]

                    source = (
                        source_rows.iloc[0]
                        if not source_rows.empty
                        else None
                    )


                    def _valid_metric(value):
                        if value is None or isinstance(value, bool):
                            return False

                        try:
                            number = float(value)
                            return (
                                number == number
                                and abs(number) != float("inf")
                            )
                        except (TypeError, ValueError, OverflowError):
                            return False

                    def _short_name(name, limit=42):
                        name = str(name or "Unnamed product").split("|")[0].strip()
                        return name if len(name) <= limit else name[:limit - 3].rstrip() + "..."

                    st.markdown("### ShopWise Alternative Insights")
                    st.caption(
                        "Compare the lowest-priced option, the closest text match, "
                        "and the highest-rated option among the returned alternatives. "
                        "The cards rank each criterion separately; the table is ranked "
                        "by the overall alternative score."
                    )
                    budget_pick = None
                    if "discounted_price_inr" in alternatives.columns:
                        priced = alternatives[
                            alternatives["discounted_price_inr"].apply(
                                lambda value: _valid_metric(value)
                                and float(value) >= 0
                            )
                        ]
                        if not priced.empty:
                            budget_pick = priced.sort_values(
                                ["discounted_price_inr", "product_id"],
                                ascending=[True, True],
                                kind="stable",
                            ).iloc[0]

                    closest_match = None
                    if "similarity_score" in alternatives.columns:
                        similar = alternatives[
                            alternatives["similarity_score"].apply(
                                _valid_metric
                            )
                        ]
                        if not similar.empty:
                            closest_match = similar.sort_values(
                                ["similarity_score", "product_id"],
                                ascending=[False, True],
                                kind="stable",
                            ).iloc[0]

                    rating_pick = None
                    if "rating" in alternatives.columns:
                        rated = alternatives[
                            alternatives["rating"].apply(
                                lambda value: _valid_metric(value)
                                and 0 <= float(value) <= 5
                            )
                        ]
                        if not rated.empty:
                            rating_pick = rated.sort_values(
                                ["rating", "product_id"],
                                ascending=[False, True],
                                kind="stable",
                            ).iloc[0]

                    insight_cols = st.columns(3, gap="small")

                    with insight_cols[0]:
                        with st.container(border=True):
                            st.markdown("**LOWEST-PRICED ALTERNATIVE**")
                            if budget_pick is not None:
                                st.markdown(
                                    f"**{_short_name(budget_pick['product_name'])}**"
                                )
                                st.metric(
                                    "Price",
                                    f"₹{float(budget_pick['discounted_price_inr']):,.0f}",
                                )

                                if source is not None and _valid_metric(
                                    source.get("discounted_price_inr")
                                ):
                                    source_price = float(
                                        source["discounted_price_inr"]
                                    )
                                    candidate_price = float(
                                        budget_pick["discounted_price_inr"]
                                    )
                                    difference = source_price - candidate_price


                                    if difference > 0:
                                        st.caption(
                                            f"₹{difference:,.0f} less than the selected product."
                                        )
                                    elif difference < 0:
                                        st.caption(
                                            f"₹{abs(difference):,.0f} more than the selected product."
                                        )

                                    else:
                                        st.caption(
                                            "Same listed price as the selected product."
                                        )
                                else:
                                    st.caption(
                                        "Selected product price unavailable for comparison."
                                    )
                            else:
                                st.caption("No valid alternative prices available.")

                    with insight_cols[1]:
                        with st.container(border=True):
                            st.markdown("**HIGHEST TEXT SIMILARITY**")
                            if closest_match is not None:
                                st.markdown(
                                    f"**{_short_name(closest_match['product_name'])}**"
                                )
                                st.metric(
                                    "Text similarity",
                                    f"{float(closest_match['similarity_score']):.2f}",
                                )
                                st.caption(
                                    "Highest text similarity among returned alternatives."
                                )
                            else:
                                st.caption("Similarity information unavailable.")

                    with insight_cols[2]:
                        with st.container(border=True):
                            st.markdown("**HIGHEST RATED**")
                            if rating_pick is not None:
                                st.markdown(
                                    f"**{_short_name(rating_pick['product_name'])}**"
                                )
                                st.metric(
                                    "Listed rating",
                                    f"{float(rating_pick['rating']):.1f} / 5",
                                )

                                if (
                                    source is not None
                                    and _valid_metric(source.get("rating"))
                                    and 0 <= float(source["rating"]) <= 5
                                ):
                                    rating_difference = (
                                        float(rating_pick["rating"])
                                        - float(source["rating"])
                                    )
                                    if rating_difference > 0:
                                        st.caption(
                                            f"{rating_difference:.1f} points above the selected product."
                                        )
                                    elif rating_difference < 0:
                                        st.caption(
                                            f"{abs(rating_difference):.1f} points below the selected product."
                                        )
                                    else:
                                        st.caption(
                                            "Same listed rating as the selected product."
                                        )
                                else:
                                    st.caption(
                                        "Selected product rating unavailable for comparison."
                                    )
                            else:
                                st.caption("No valid alternative ratings available.")

                    st.divider()


                    desired_columns = [
                        "product_name",
                        "discounted_price_inr",
                        "rating",
                        "similarity_score",
                        "alternative_score",
                    ]

                    display = alternatives[
                        [
                            column
                            for column in desired_columns
                            if column in alternatives.columns
                        ]
                    ].rename(
                        columns={
                            "product_name": "Product",
                            "discounted_price_inr": "Price (INR)",
                            "rating": "Rating",
                            "similarity_score": "Text similarity",
                            "alternative_score": "Alternative score",
                        }
                    ).copy()

                    column_config = {}

                    if "Product" in display.columns:
                        column_config["Product"] = st.column_config.TextColumn(
                            "Product",
                            help="Full product name. Hover over a cell to inspect its contents.",
                            width="medium",
                        )

                    if "Price (INR)" in display.columns:
                        column_config["Price (INR)"] = (
                            st.column_config.NumberColumn(
                                "Price (INR)",
                                format="INR %.0f",
                                width="small",
                            )
                        )

                    if "Rating" in display.columns:
                        column_config["Rating"] = st.column_config.NumberColumn(
                            "Rating",
                            format="%.1f",
                            width="small",
                        )

                    if "Text similarity" in display.columns:
                        column_config["Text similarity"] = (
                            st.column_config.NumberColumn(
                                "Text similarity",
                                format="%.2f",
                                width="small",
                            )
                        )

                    if "Alternative score" in display.columns:
                        column_config["Alternative score"] = (
                            st.column_config.NumberColumn(
                                "Alternative score",
                                format="%.2f",
                                width="small",
                            )
                        )

                    st.dataframe(
                        display,
                        use_container_width=True,
                        hide_index=True,
                        column_config=column_config,
                    )

                    st.caption(
                        "Similarity scores compare product text, while the "
                        "alternative score combines text similarity and price "
                        "proximity when the selected product has a valid price. "
                        "Neither score guarantees equivalent features."
                    )


            except (ValueError, KeyError, RuntimeError) as exc:
                st.error(f"Unable to find alternatives: {exc}")

st.divider()
st.caption(
    "ShopWise AI uses a public product dataset. Prices, ratings, and "
    "descriptions may be outdated or inaccurate. Verify details on the "
    "seller's page before purchasing."
)
