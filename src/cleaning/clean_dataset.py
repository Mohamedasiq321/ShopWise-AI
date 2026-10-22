
import csv
import re
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_FILE = PROJECT_ROOT / "data" / "raw" / "amazon.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

TARGET_CATEGORY = "Computers&Accessories"

PRODUCT_FIELDS = [
    "product_name",
    "category",
    "discounted_price",
    "actual_price",
    "discount_percentage",
    "rating",
    "rating_count",
    "about_product",
    "img_link",
    "product_link",
]

URL_PATTERN = re.compile(r"https?://[^\s,]+", re.IGNORECASE)


def parse_number(value):
    """Parse numeric values such as '24,269', '4.2' or '64%'."""
    if not value:
        return None

    cleaned = value.replace(",", "").replace("%", "").strip()

    try:
        number = float(cleaned)
        return number if number >= 0 else None
    except ValueError:
        return None


def parse_inr(value):
    """Convert values such as ₹1,099 into numeric INR."""
    if not value:
        return None

    cleaned = value.replace("₹", "").replace(",", "").strip()

    try:
        number = float(cleaned)
        return number if number >= 0 else None
    except ValueError:
        return None


def is_valid_http_url(value):
    """Basic validation for a usable HTTP or HTTPS URL."""
    if not value:
        return False

    try:
        parsed = URL_PATTERN.match(value.strip())
        if not parsed:
            return False

        from urllib.parse import urlsplit
        parts = urlsplit(value.strip())
        return parts.scheme in {"http", "https"} and bool(parts.netloc)
    except ValueError:
        return False


def clean_review_text(value):
    """Remove embedded URLs from a copy; do not split review fragments."""
    return URL_PATTERN.sub("", value or "").strip()


def load_source():
    if not RAW_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {RAW_FILE}\n"
            "Ensure data/raw/amazon.csv exists."
        )

    with RAW_FILE.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        columns = reader.fieldnames or []

        required = {
            "product_id",
            "product_name",
            "category",
            "discounted_price",
            "actual_price",
            "rating",
            "rating_count",
            "about_product",
            "review_title",
            "review_content",
        }

        missing = required - set(columns)
        if missing:
            raise ValueError(
                f"Missing required columns: {sorted(missing)}"
            )

        rows = []
        for row_number, row in enumerate(reader, start=2):
            row["_source_row_number"] = row_number
            rows.append(row)

    return columns, rows


def row_completeness(row):
    """Count non-empty product fields for a deterministic tie-break."""
    return sum(
        bool((row.get(field) or "").strip())
        for field in PRODUCT_FIELDS
    )


def choose_representative_row(rows):
    """
    Choose one COMPLETE source row.

    Rule:
    1. Prefer the longest non-empty product description.
    2. Then prefer the row with the most populated product fields.
    3. If still tied, prefer the earliest row in the original CSV.

    This is a reproducible selection rule, not proof that the selected
    row is the newest or historically correct version.
    """
    return max(
        rows,
        key=lambda row: (
            len((row.get("about_product") or "").strip()),
            row_completeness(row),
            -int(row["_source_row_number"]),
        ),
    )


def write_csv(path, rows, fieldnames):
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    source_columns, source_rows = load_source()

    category_rows = [
        row for row in source_rows
        if (row.get("category") or "").split("|")[0].strip()
        == TARGET_CATEGORY
    ]

    grouped = defaultdict(list)

    for row in category_rows:
        product_id = (row.get("product_id") or "").strip()
        if product_id:
            grouped[product_id].append(row)

    products = []
    conflict_audit = []
    description_audit = []
    review_source_audit = []

    for product_id, rows in grouped.items():
        chosen = choose_representative_row(rows)
        chosen_row_number = int(chosen["_source_row_number"])

        # Keep the selected record intact: all fields come from one source row.
        product = {
            field: chosen.get(field, "")
            for field in PRODUCT_FIELDS
        }

        product["product_id"] = product_id
        product["source_row_number"] = chosen_row_number
        product["source_rows_for_product"] = len(rows)

        product["discounted_price_inr"] = parse_inr(
            chosen.get("discounted_price", "")
        )
        product["actual_price_inr"] = parse_inr(
            chosen.get("actual_price", "")
        )
        product["discount_percentage_numeric"] = parse_number(
            chosen.get("discount_percentage", "")
        )
        product["rating_numeric"] = parse_number(
            chosen.get("rating", "")
        )
        product["rating_count_numeric"] = parse_number(
            chosen.get("rating_count", "")
        )

        rating = product["rating_numeric"]
        if rating is not None and not 0 <= rating <= 5:
            raise ValueError(
                f"Invalid rating for product {product_id}: {rating}"
            )

        products.append(product)

        # Audit all differing product fields for duplicate groups.
        differing_fields = [
            field
            for field in PRODUCT_FIELDS
            if len({
                (row.get(field) or "").strip()
                for row in rows
            }) > 1
        ]

        if len(rows) > 1 and differing_fields:
            conflict_audit.append({
                "product_id": product_id,
                "source_row_numbers": ";".join(
                    str(row["_source_row_number"]) for row in rows
                ),
                "chosen_source_row_number": chosen_row_number,
                "duplicate_row_count": len(rows),
                "conflicting_fields": ";".join(differing_fields),
                "selection_rule": (
                    "longest_description_then_completeness_then_earliest_row"
                ),
            })

        # Preserve every distinct description variant for manual review.
        distinct_descriptions = list(dict.fromkeys(
            (row.get("about_product") or "").strip()
            for row in rows
        ))

        for variant_number, description in enumerate(
            distinct_descriptions, start=1
        ):
            matching_rows = [
                row for row in rows
                if (row.get("about_product") or "").strip() == description
            ]

            description_audit.append({
                "product_id": product_id,
                "variant_number": variant_number,
                "source_row_numbers": ";".join(
                    str(row["_source_row_number"])
                    for row in matching_rows
                ),
                "selected_for_product": (
                    description
                    == (chosen.get("about_product") or "").strip()
                ),
                "description": description,
            })

        # Preserve source review fields; they are not yet individual reviews.
        for row in rows:
            raw_content = row.get("review_content", "")
            raw_title = row.get("review_title", "")
            urls = URL_PATTERN.findall(raw_content)

            review_source_audit.append({
                "product_id": product_id,
                "source_row_number": row["_source_row_number"],
                "review_title_raw": raw_title,
                "review_content_raw": raw_content,
                "review_content_without_urls": clean_review_text(raw_content),
                "embedded_url_count": len(urls),
                "review_boundaries_verified": "false",
            })

    product_fields = [
        "product_id",
        *PRODUCT_FIELDS,
        "source_row_number",
        "source_rows_for_product",
        "discounted_price_inr",
        "actual_price_inr",
        "discount_percentage_numeric",
        "rating_numeric",
        "rating_count_numeric",
    ]

    write_csv(
        OUTPUT_DIR / "products.csv",
        products,
        product_fields,
    )

    write_csv(
        OUTPUT_DIR / "product_conflict_audit.csv",
        conflict_audit,
        [
            "product_id",
            "source_row_numbers",
            "chosen_source_row_number",
            "duplicate_row_count",
            "conflicting_fields",
            "selection_rule",
        ],
    )

    write_csv(
        OUTPUT_DIR / "description_variants_audit.csv",
        description_audit,
        [
            "product_id",
            "variant_number",
            "source_row_numbers",
            "selected_for_product",
            "description",
        ],
    )

    write_csv(
        OUTPUT_DIR / "review_text_audit.csv",
        review_source_audit,
        [
            "product_id",
            "source_row_number",
            "review_title_raw",
            "review_content_raw",
            "review_content_without_urls",
            "embedded_url_count",
            "review_boundaries_verified",
        ],
    )

    invalid_prices = sum(
        product["discounted_price_inr"] is None
        for product in products
    )
    invalid_ratings = sum(
        product["rating_numeric"] is None
        or not 0 <= product["rating_numeric"] <= 5
        for product in products
    )

    print("\n========== CLEANING SUMMARY ==========")
    print("Source CSV rows:", len(source_rows))
    print("Selected category rows:", len(category_rows))
    print("Unique product IDs:", len(products))
    print("Duplicate groups with conflicts:", len(conflict_audit))
    print("Distinct description variants:", len(description_audit))
    print("Review source rows preserved:", len(review_source_audit))
    print("Products with invalid discounted prices:", invalid_prices)
    print("Products with missing/invalid ratings:", invalid_ratings)

    print("\n========== OUTPUT FILES ==========")
    for name in [
        "products.csv",
        "product_conflict_audit.csv",
        "description_variants_audit.csv",
        "review_text_audit.csv",
    ]:
        print(OUTPUT_DIR / name)

    print("\nOriginal CSV was not modified.")
    print("Review boundaries remain unverified.")
    print("Representative-row selection is deterministic, not time-based.")


if __name__ == "__main__":
    main()
