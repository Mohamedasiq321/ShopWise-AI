"""Explainable product search and recommendation for ShopWise AI."""

from pathlib import Path
import sqlite3

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from src.recommendation.query_intent import detect_query_intent


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "processed" / "shopwise.db"


class ProductRecommendationEngine:
    """Search, rank, compare, and recommend products from SQLite."""

    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = Path(db_path)

        if not self.db_path.is_file():
            raise FileNotFoundError(
                f"Product database not found: {self.db_path}"
            )

        self.products = self._load_products()

        if self.products.empty:
            raise ValueError("The product database contains no products.")

        self.products["search_text"] = (
            self.products["product_name"].fillna("").astype(str)
            + " "
            + self.products["about_product"].fillna("").astype(str)
            + " "
            + self.products["category"].fillna("").astype(str)
        ).str.lower()

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=30000,
            sublinear_tf=True,
        )

        self.product_matrix = self.vectorizer.fit_transform(
            self.products["search_text"]
        )
        self.title_matrix = self.vectorizer.transform(
            self.products["product_name"].fillna("").astype(str).str.lower()
        )

        self.category_text = (
            self.products["category"]
            .fillna("")
            .astype(str)
            .str.replace(r"[&|]", " ", regex=True)
            .str.replace(r"(?<=[a-z])(?=[A-Z])", " ", regex=True)
            .str.lower()
        )

        self.category_matrix = self.vectorizer.transform(self.category_text)

    def _load_products(self):
        """Load product records without modifying the database."""
        uri = self.db_path.resolve().as_uri() + "?mode=ro"

        with sqlite3.connect(uri, uri=True) as connection:
            products = pd.read_sql_query(
                """
                SELECT
                    product_id,
                    product_name,
                    category,
                    discounted_price_inr,
                    actual_price_inr,
                    discount_percentage,
                    rating,
                    rating_count,
                    about_product,
                    img_link,
                    product_link
                FROM products
                ORDER BY product_id
                """,
                connection,
            )

        numeric_columns = [
            "discounted_price_inr",
            "actual_price_inr",
            "discount_percentage",
            "rating",
            "rating_count",
        ]

        for column in numeric_columns:
            products[column] = pd.to_numeric(
                products[column], errors="coerce"
            )

        products["product_id"] = products["product_id"].astype(str)
        products["product_name"] = (
            products["product_name"].fillna("").astype(str)
        )

        return products


    @staticmethod
    def _matches_product_intent(product_name, intent):
        """Check whether a product title matches a recognized product type."""
        import re

        name = re.sub(r"\s+", " ", str(product_name or "").lower()).strip()
        product_type = intent.product_type

        if not product_type:
            return True

        if any(term in name for term in intent.excluded_terms):
            return False

        if product_type == "gaming_mouse":
            return (
                "gaming" in name
                and re.search(r"\b(?:mouse|mice)\b", name) is not None
                and not any(term in name for term in ("mousepad", "mouse pad", "mouse mat"))
            )

        if product_type == "usb_c_cable":
            has_cable = "cable" in name
            has_usb_c = re.search(
                r"\b(?:usb[\s-]*c|type[\s-]*c)\b", name
            ) is not None
            is_lightning_cable = re.search(r"\blightning\b", name) is not None
            return has_cable and has_usb_c and not is_lightning_cable

        if product_type == "webcam":
            has_camera = re.search(
                r"\b(?:webcams?|web\s+cameras?)\b", name
            ) is not None

            is_standalone_accessory = re.search(
                r"\b(?:webcam|web\s+camera)\s+"
                r"(?:cover|protector|blocker)\b"
                r"|\bcamera\s+privacy\s+covers?\b"
                r"|\bprivacy\s+covers?\b"
                r"|\bcover\s+slide\b",
                name,
            ) is not None

            return has_camera and not is_standalone_accessory

        if product_type == "wireless_earbuds":
            return (
                re.search(r"\bearbuds?\b", name) is not None
                and not any(
                    term in name
                    for term in ("earbud case", "earbud cover")
                )
            )

        if product_type == "soundbar":
            return (
                re.search(r"\bsound\s*bars?\b", name) is not None
                and not any(
                    term in name
                    for term in ("cover", "wall mount", "remote control")
                )
            )

        if product_type == "bluetooth_speaker":
            return (
                "bluetooth" in name
                and re.search(r"\bspeakers?\b", name) is not None
                and not any(term in name for term in ("adapter", "dongle"))
            )

        if product_type == "external_hard_drive":
            has_drive = re.search(
                r"\b(?:hard[\s-]+drive|hard[\s-]+disk[\s-]+drive|hdd)\b",
                name,
            ) is not None
            has_portable_or_external = (
                "portable" in name or "external" in name
            )
            return has_drive and has_portable_or_external


        if product_type == "wireless_keyboard_combo":
            has_keyboard = re.search(r"\bkeyboards?\b", name) is not None
            has_mouse = re.search(r"\bmouse\b", name) is not None

            is_combo = any(
                term in name
                for term in (
                    "keyboard and mouse",
                    "keyboard & mouse",
                    "keyboard mouse combo",
                    "keyboard combo",
                    "keyboard and mouse set",
                    "keyboard set",
                )
            )

            has_wireless_signal = any(
                term in name
                for term in ("wireless", "bluetooth", "2.4ghz", "2.4 ghz")
            )

            return (
                has_keyboard
                and has_mouse
                and is_combo
                and has_wireless_signal
                and "wired" not in name
            )


        if product_type == "wireless_keyboard":
            has_keyboard = (
                re.search(r"\bkeyboards?\b", name) is not None
            )
            has_wireless_signal = any(
                term in name
                for term in ("wireless", "bluetooth")
            )
            is_accessory = any(
                term in name
                for term in (
                    "keyboard cover",
                    "keyboard case",
                    "keycap",
                )
            )
            is_combo = (
                "mouse" in name
                and any(
                    term in name
                    for term in (
                        "combo",
                        "set",
                        "keyboard and mouse",
                        "keyboard & mouse",
                    )
                )
            )

            return (
                has_keyboard
                and has_wireless_signal
                and not is_accessory
                and not is_combo
            )


        return True

    @staticmethod
    def _category_candidates(query, results):
        """Filter clear product-type searches using normalized category leaves."""
        import re

        if results.empty or not query:
            return results

        def tokens(value):
            value = str(value or "")
            value = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", value)
            value = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", value)
            value = value.lower().replace("mousepad", "mouse pad")
            words = re.findall(r"[a-z0-9]+", value)
            aliases = {
                "mice": "mouse", "mouses": "mouse",
                "keyboards": "keyboard", "cables": "cable",
                "webcams": "webcam", "speakers": "speaker",
                "adapters": "adapter", "drives": "drive",
                "disks": "disk", "pads": "pad",
                "earbuds": "earbud", "headphones": "headset", "headphone": "headset", "headsets": "headset", "headset": "headset",
                "laptops": "laptop", "tablets": "tablet",
                "monitors": "monitor", "printers": "printer",
                "routers": "router", "chargers": "charger",
                "hubs": "hub", "cases": "case", "covers": "cover",
                "sets": "set", "gamepads": "gamepad",
                "pendrives": "pendrive",
                "chargers": "charger", "sleeves": "sleeve",
                "bags": "bag", "mats": "mat", "covers": "cover",
                "cases": "case", "accessories": "accessory",
            }
            return [aliases.get(word, word) for word in words]

        ignored = {
            "a", "an", "and", "for", "in", "of", "the", "to", "with",
            "best", "cheap", "top", "product", "products", "buy", "under",
        }
        attributes = {
            "wireless", "wired", "bluetooth", "gaming", "portable",
            "external", "fast", "charging", "rechargeable", "silent",
            "budget", "premium", "new",
        }

        query_tokens = set(tokens(query)) - ignored
        requested = query_tokens - attributes
        if not requested:
            return results

        leaves = results["category"].fillna("").astype(str).map(
            lambda category: set(tokens(category.split("|")[-1]))
        )
        catalogue_vocabulary = set().union(*leaves.tolist()) if len(leaves) else set()
        recognized = requested & catalogue_vocabulary

        # If no catalogue category supports the query's product terms,
        # leave the existing text search untouched.
        if not recognized:
            return results

        accessory_terms = {
            "accessory", "accessories", "pad", "mat", "case", "cover",
            "protector", "set", "combo", "cable", "adapter", "dongle",
            "mount", "sleeve", "bag", "caddy", "stand", "holder",
            "replacement", "charger",
        }
        explicitly_requested = query_tokens
        eligible = []

        for leaf in leaves:
            # Every recognized product-type term must match the category.
            matches_type = recognized.issubset(leaf)
            has_unrequested_accessory = bool(
                (leaf & accessory_terms) - explicitly_requested
            )
            eligible.append(matches_type and not has_unrequested_accessory)

        filtered = results.loc[eligible]
        return filtered if not filtered.empty else results

    @staticmethod
    def _validate_budget(max_budget):
        if max_budget is None:
            return None

        if isinstance(max_budget, bool):
            raise ValueError("Budget must be a positive number.")

        try:
            budget = float(max_budget)
        except (TypeError, ValueError):
            raise ValueError("Budget must be a valid number.") from None

        if not pd.notna(budget) or budget <= 0:
            raise ValueError("Budget must be greater than zero.")

        return budget

    def search(self, query="", max_budget=None, min_rating=None, limit=10):
        """
        Find and rank products.

        Ranking = 75% text relevance + 25% normalized customer rating.
        For a blank query, ranking is based on rating alone.

        Budget and minimum-rating filters are applied before ranking.
        """
        budget = self._validate_budget(max_budget)

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer.")

        if min_rating is not None:
            try:
                min_rating = float(min_rating)
            except (TypeError, ValueError):
                raise ValueError("Minimum rating must be numeric.") from None

            if not 0 <= min_rating <= 5:
                raise ValueError("Minimum rating must be between 0 and 5.")

        query = str(query or "").strip()
        results = self.products.copy()

        if budget is not None:
            results = results[
                results["discounted_price_inr"].notna()
                & (results["discounted_price_inr"] <= budget)
            ]


        if min_rating is not None:
            results = results[
                results["rating"].notna()
                & (results["rating"] >= min_rating)
            ]

        intent = detect_query_intent(query)

        if query and intent.product_type:
            matches_intent = results["product_name"].apply(
                lambda name: self._matches_product_intent(name, intent)
            )
            results = results[matches_intent]
        elif query:
            results = self._category_candidates(query, results)

        if query and not results.empty:
            results = results[
                self.vectorizer.transform(
                    results["search_text"]
                ).getnnz(axis=1) > 0
            ]

        if results.empty:

            return results.assign(
                relevance_score=pd.Series(dtype=float),
                rating_score=pd.Series(dtype=float),
                recommendation_score=pd.Series(dtype=float),
                explanation=pd.Series(dtype=str),
            )

        # Keep ranking calculations aligned with the filtered product rows.
        positions = results.index.to_numpy()

        if query:
            query_vector = self.vectorizer.transform([query.lower()])

            title_relevance = cosine_similarity(
                query_vector, self.title_matrix[positions]
            ).ravel()

            description_relevance = cosine_similarity(
                query_vector, self.product_matrix[positions]
            ).ravel()

            category_relevance = cosine_similarity(
                query_vector, self.category_matrix[positions]
            ).ravel()

            relevance = (
                0.60 * title_relevance
                + 0.25 * description_relevance
                + 0.15 * category_relevance
            )
        else:
            relevance = [0.0] * len(results)

        # Ratings are normalized to [0, 1]. Missing ratings receive 0.
        rating_score = (
            results["rating"].fillna(0).clip(0, 5).to_numpy() / 5.0
        )

        if query:
            recommendation_score = (
                0.75 * relevance + 0.25 * rating_score
            )
        else:
            recommendation_score = rating_score

        results["relevance_score"] = relevance
        results["rating_score"] = rating_score
        results["recommendation_score"] = recommendation_score

        def explain(row):
            reasons = []

            if query and row["relevance_score"] > 0:
                reasons.append("matches your search terms")

            if pd.notna(row["rating"]):
                reasons.append(f"rated {row['rating']:.1f}/5")

            if budget is not None:
                reasons.append("within your budget")

            if not reasons:
                return "Limited product information is available."

            return "Recommended because it " + " and ".join(reasons) + "."

        results["explanation"] = results.apply(explain, axis=1)

        results = results.sort_values(
            by=[
                "recommendation_score",
                "rating",
                "product_id",
            ],
            ascending=[False, False, True],
            na_position="last",
            kind="stable",
        )

        return results.head(limit).reset_index(drop=True)

    def compare(self, product_ids):
        """Return selected products for side-by-side comparison."""
        if isinstance(product_ids, (str, bytes)):
            raise ValueError("Provide a list of at least two product IDs.")

        product_ids = list(dict.fromkeys(str(pid) for pid in product_ids))

        if len(product_ids) < 2:
            raise ValueError("Select at least two distinct products.")

        selected = self.products[
            self.products["product_id"].isin(product_ids)
        ].copy()

        found_ids = set(selected["product_id"])
        missing_ids = set(product_ids) - found_ids

        if missing_ids:
            raise ValueError(
                "Unknown product IDs: " + ", ".join(sorted(missing_ids))
            )

        selected["discounted_price_inr"] = selected[
            "discounted_price_inr"
        ].round(2)

        return (
            selected.set_index("product_id")
            .loc[product_ids]
            .reset_index()
        )



    @staticmethod
    def _alternative_family(product):
        """Classify products into compatible alternative families."""
        import re

        name = str(product.get("product_name", "") or "").lower()
        category = str(product.get("category", "") or "")
        leaf = category.split("|")[-1]

        leaf = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", leaf)
        leaf = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", leaf)
        leaf = re.sub(r"[&_/]+", " ", leaf)
        leaf = re.sub(r"\s+", " ", leaf).strip().lower()

        combined = f"{leaf} {name}"

                # Exclude adapters and other accessories before device keyword matching.
        if re.search(
            r"\b(?:bluetooth|wireless|usb)\s+adapters?\b"
            r"|\bdongles?\b"
            r"|\b(?:receivers?|transmitters?)\b",
            name,
        ):
            return "accessory"

        # Classify accessories before devices mentioned in their names.

        # Trust the specific product category before accessory keywords
        # appearing in a device's marketing description.
        if "webcams" in leaf:
            return "webcam"

        if re.search(
            r"\b(?:webcam|web\s*camera)\s+(?:cover|blocker|protector)\b"
            r"|\b(?:camera\s*privacy\s*covers?|privacy\s*covers?)\b"
            r"|\bcover\s+slide\b",
            combined,
        ) or "camera privacy covers" in combined:
            return "webcam_accessory"

        if re.search(
            r"\bkeyboard\b.*\b(?:covers?|protectors?|skins?)\b"
            r"|\bkeycaps?\b|\bdust\s*covers?\b",
            combined,
        ):
            return "keyboard_accessory"

        if re.search(
            r"\bmouse\s*pad\b|\bmouse\s*mat\b|\bmousepad\b",
            combined,
        ):
            return "mousepad"

        if re.search(
            r"\blaptop\s+sleeves?\b|\bslipcases?\b",
            combined,
        ):
            return "laptop_sleeve"

        # Keep keyboard-and-mouse sets separate from standalone keyboards.
        if (
            "keyboard" in combined
            and re.search(r"\bmouse\b", name)
            and re.search(
                r"\b(?:combo|set)\b"
                r"|keyboard\s*(?:and|&|\+)\s*mouse",
                name,
            )
        ):
            return "keyboard_mouse_combo"

        # Distinguish wireless, wired, and unspecified standalone keyboards.
        if "keyboard" in leaf or re.search(r"\bkeyboard\b", name):
            if re.search(
                r"\bwireless\b|\bbluetooth\b|\b2\.4\s*ghz\b",
                name,
            ):
                return "wireless_keyboard"

            if re.search(r"\bwired\b", name):
                return "wired_keyboard"

            return "keyboard"

        # Accessories have already been excluded above.
        if re.search(r"\b(?:web\s*cameras?|webcams?)\b", combined):
            return "webcam"

        if re.search(r"\b(?:gaming\s+)?mice\b|\bmouse\b", combined):
            return "mouse"

        if "cable" in combined:
            if re.search(r"\b(?:usb[\s-]*c|type[\s-]*c)\b", name):
                return "usb_c_cable"
            if "lightning" in name:
                return "lightning_cable"
            if re.search(r"\bmicro[\s-]*usb\b", name):
                return "micro_usb_cable"
            return "cable"

        if re.search(r"\bearbuds?\b", combined):
            return "earbuds"

        if re.search(r"\bsound\s*bars?\b", combined):
            return "soundbar"

        if re.search(r"\bspeakers?\b", combined):
            return "speaker"

        if re.search(r"\bheadphones?\b|\bheadsets?\b", combined):
            return "headset"

        if re.search(
            r"\b(?:external|portable)\s+(?:hard\s+)?(?:drive|disk)\b"
            r"|\bhdd\b",
            combined,
        ):
            return "external_storage"

        # Conservative fallback: use the normalized category leaf.
        return f"category:{leaf}" if leaf else None


    def alternatives(self, product_id, max_budget=None, limit=5):
        """Recommend compatible products, ranked by similarity and price."""
        budget = self._validate_budget(max_budget)

        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer.")

        matches = self.products[
            self.products["product_id"] == str(product_id)
        ]

        if matches.empty:
            raise ValueError(f"Unknown product ID: {product_id}")

        source = matches.iloc[0]
        source_index = matches.index[0]
        source_family = self._alternative_family(source)

        candidates = self.products[
            self.products["product_id"] != str(product_id)
        ].copy()

        # Never recommend cross-family products just to fill the result list.
        if source_family is None:
            return candidates.iloc[0:0].assign(
                similarity_score=pd.Series(dtype=float),
                price_difference_ratio=pd.Series(dtype=float),
                alternative_score=pd.Series(dtype=float),
            )

        candidates["alternative_family"] = candidates.apply(
            self._alternative_family, axis=1
        )
        candidates = candidates[
            candidates["alternative_family"] == source_family
        ].copy()

        if budget is not None:
            candidates = candidates[
                candidates["discounted_price_inr"].notna()
                & (candidates["discounted_price_inr"] <= budget)
            ].copy()

        if candidates.empty:
            return candidates.assign(
                similarity_score=pd.Series(dtype=float),
                price_difference_ratio=pd.Series(dtype=float),
                alternative_score=pd.Series(dtype=float),
            )

        similarities = cosine_similarity(
            self.product_matrix[source_index],
            self.product_matrix[candidates.index.to_numpy()],
        ).ravel()

        candidates["similarity_score"] = similarities
        candidates = candidates[candidates["similarity_score"] > 0].copy()

        source_price = source["discounted_price_inr"]

        if pd.notna(source_price) and source_price > 0:
            candidates["price_difference_ratio"] = (
                (candidates["discounted_price_inr"] - source_price).abs()
                / source_price
            ).clip(0, 1)

            price_score = (
                1 - candidates["price_difference_ratio"]
            ).fillna(0)

            candidates["alternative_score"] = (
                0.8 * candidates["similarity_score"]
                + 0.2 * price_score
            )
        else:
            candidates["price_difference_ratio"] = float("nan")
            candidates["alternative_score"] = candidates["similarity_score"]

        return candidates.sort_values(
            ["alternative_score", "rating", "product_id"],
            ascending=[False, False, True],
            na_position="last",
            kind="stable",
        ).drop(columns=["alternative_family"]).head(limit).reset_index(drop=True)
