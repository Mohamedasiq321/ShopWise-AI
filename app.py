"""ShopWise AI: product discovery, comparison, and alternatives."""

import math

import streamlit as st
import urllib.error
import urllib.request

from src.recommendation.engine import ProductRecommendationEngine


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


def is_valid_number(value):
    """Return True for finite numeric values, excluding NaN and infinity."""
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
                        st.metric("Match score", f"{float(score):.3f}")
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

                    fields = {
                        "Product": "product_name",
                        "Price (INR)": "discounted_price_inr",
                        "Actual price (INR)": "actual_price_inr",
                        "Rating": "rating",
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

                    if "Product" in display.columns:
                        display["Product"] = (
                            display["Product"]
                            .astype(str)
                            .str.slice(0, 76)
                            .where(
                                display["Product"].astype(str).str.len() <= 76,
                                display["Product"].astype(str).str.slice(0, 73) + "...",
                            )
                        )

                    column_config = {}
                    if "Price (INR)" in display.columns:
                        column_config["Price (INR)"] = (
                            st.column_config.NumberColumn(
                                "Price (INR)",
                                format="INR %.0f",
                            )
                        )
                    if "Rating" in display.columns:
                        column_config["Rating"] = st.column_config.NumberColumn(
                            "Rating",
                            format="%.1f",
                        )
                    if "Text similarity" in display.columns:
                        column_config["Text similarity"] = (
                            st.column_config.NumberColumn(
                                "Text similarity",
                                format="%.2f",
                            )
                        )
                    if "Alternative score" in display.columns:
                        column_config["Alternative score"] = (
                            st.column_config.NumberColumn(
                                "Alternative score",
                                format="%.2f",
                            )
                        )

                    st.dataframe(
                        display,
                        use_container_width=True,
                        hide_index=True,
                        column_config=column_config,
                    )

                    st.caption(
                        "Similarity scores use product text and price proximity; "
                        "they do not guarantee equivalent features."
                    )

            except (ValueError, KeyError, RuntimeError) as exc:
                st.error(f"Unable to find alternatives: {exc}")

st.divider()
st.caption(
    "ShopWise AI uses a public product dataset. Prices, ratings, and "
    "descriptions may be outdated or inaccurate. Verify details on the "
    "seller's page before purchasing."
)
