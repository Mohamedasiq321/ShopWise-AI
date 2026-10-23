
"""ShopWise AI — interactive product discovery and comparison."""

import streamlit as st

from src.recommendation.engine import ProductRecommendationEngine


st.set_page_config(
    page_title="ShopWise AI | Smart Shopping",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource
def load_engine():
    return ProductRecommendationEngine()


engine = load_engine()

st.title("🛍️ ShopWise AI")
st.caption(
    "Find products, compare options, and explore alternatives "
    "using transparent, data-driven recommendations."
)

with st.sidebar:
    st.header("Shopping preferences")

    query = st.text_input(
        "What are you looking for?",
        placeholder="e.g. wireless mouse, USB-C cable",
    )

    max_budget = st.number_input(
        "Maximum budget (₹)",
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

# Keep the current search results available to the comparison workflow.
if "shopwise_results" not in st.session_state:
    st.session_state.shopwise_results = None

if "shopwise_query" not in st.session_state:
    st.session_state.shopwise_query = ""

if search_clicked:
    try:
        results = engine.search(
            query=query,
            max_budget=max_budget if max_budget > 0 else None,
            min_rating=min_rating if min_rating > 0 else None,
            limit=result_limit,
        )
        st.session_state.shopwise_results = results
        st.session_state.shopwise_query = query
    except (ValueError, RuntimeError) as exc:
        st.error(f"Unable to search products: {exc}")

results = st.session_state.shopwise_results

tab_discover, tab_compare, tab_alternatives = st.tabs(
    ["🔎 Discover", "⚖️ Compare", "🔄 Alternatives"]
)

with tab_discover:
    st.subheader("Product discovery")

    if results is None:
        st.info(
            "Enter a product or feature in the sidebar and select "
            "**Find products**. You can also leave the query blank "
            "to browse highly rated products."
        )
    elif results.empty:
        st.warning(
            "No products matched those filters. Try a different "
            "search term, a higher budget, or a lower rating."
        )
    else:
        st.write(f"Showing **{len(results)}** matching products.")

        for _, product in results.iterrows():
            with st.container(border=True):
                left, right = st.columns([4, 1])

                with left:
                    st.markdown(f"### {product['product_name']}")

                    price = product["discounted_price_inr"]
                    actual_price = product["actual_price_inr"]
                    rating = product["rating"]
                    discount = product["discount_percentage"]

                    if price == price:
                        st.markdown(f"**Price: ₹{price:,.2f}**")

                    details = []

                    if rating == rating:
                        details.append(f"⭐ {rating:.1f}/5")

                    if discount == discount:
                        details.append(f"{discount:.0f}% listed discount")

                    if details:
                        st.caption(" · ".join(details))

                    description = str(product["about_product"] or "").strip()
                    if description:
                        st.write(
                            description[:500]
                            + ("…" if len(description) > 500 else "")
                        )

                    st.caption(str(product["explanation"]))

                    product_url = str(product["product_link"] or "").strip()
                    if product_url.startswith(("https://", "http://")):
                        st.markdown(f"[View product page]({product_url})")

                with right:
                    st.metric(
                        "Match score",
                        f"{product['recommendation_score']:.3f}",
                    )

                    if (
                        price == price
                        and actual_price == actual_price
                        and actual_price > 0
                    ):
                        savings = actual_price - price
                        st.caption(f"Listed savings: ₹{savings:,.2f}")

with tab_compare:
    st.subheader("Compare products")

    if results is None or results.empty:
        st.info("Search for products first, then select products to compare.")
    else:
        available = {
            f"{row.product_name[:100]} — {row.product_id}": row.product_id
            for row in results.itertuples()
        }

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
                        "Price (₹)": "discounted_price_inr",
                        "Actual price (₹)": "actual_price_inr",
                        "Rating": "rating",
                        "Discount (%)": "discount_percentage",
                        "Description": "about_product",
                    }


                    table = comparison[
                        list(fields.values())
                    ].rename(
                        columns={column: label for label, column in fields.items()}
                    ).set_index("Product").T

                    st.dataframe(
                        table.astype(str),
                        use_container_width=True,
                    )

                except ValueError as exc:
                    st.error(str(exc))

with tab_alternatives:
    st.subheader("Find alternatives")

    if results is None or results.empty:
        st.info("Search for a product first to explore similar alternatives.")
    else:
        choices = {
            f"{row.product_name[:100]} — {row.product_id}": row.product_id
            for row in results.itertuples()
        }

        selected_label = st.selectbox(
            "Choose a product",
            options=list(choices.keys()),
            key="shopwise_alternative_source",
        )

        alternative_budget = st.number_input(
            "Alternative budget limit (₹)",
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
                        alternative_budget if alternative_budget > 0 else None
                    ),
                    limit=5,
                )

                if alternatives.empty:
                    st.warning(
                        "No similar alternatives found under those constraints."
                    )
                else:
                    st.dataframe(
                        alternatives[
                            [
                                "product_name",
                                "discounted_price_inr",
                                "rating",
                                "similarity_score",
                                "alternative_score",
                            ]
                        ].rename(
                            columns={
                                "product_name": "Product",
                                "discounted_price_inr": "Price (₹)",
                                "rating": "Rating",
                                "similarity_score": "Text similarity",
                                "alternative_score": "Alternative score",
                            }
                        ),
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(
                        "Similarity scores are based on product text and price "
                        "proximity, not verified feature equivalence."
                    )

            except ValueError as exc:
                st.error(str(exc))

st.divider()
st.caption(
    "ShopWise AI uses a public product dataset. Prices, ratings, and "
    "descriptions may be outdated or inaccurate. Verify details on the "
    "seller's page before purchasing."
)
