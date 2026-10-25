import csv
import hashlib
import json
import sqlite3
from pathlib import Path

ROOT = Path.cwd()
DB = ROOT / "data/processed/shopwise.db"
STAGING = ROOT / "data/processed/staging/flipkart_speakers_staging.csv"
OUT = ROOT / "data/processed/staging"

PC_SPEAKERS = (
    "Computers&Accessories|Accessories&Peripherals|"
    "Audio&VideoAccessories|PCSpeakers"
)
PC_HEADSETS = (
    "Computers&Accessories|Accessories&Peripherals|"
    "Audio&VideoAccessories|PCHeadsets"
)

def normalize(value):
    return " ".join((value or "").casefold().split())

def make_id(name):
    digest = hashlib.sha256(normalize(name).encode("utf-8")).hexdigest()[:16]
    return "EXT_FLIPKART_" + digest

def category_for(name):
    low = name.casefold()
    if any(term in low for term in ("earbud", "earphone", "headphone", "truke buds")):
        return PC_HEADSETS, "HEADSET_MAPPING_REVIEW"
    if "speaker" in low or "soundbar" in low:
        return PC_SPEAKERS, "SPEAKER_MAPPING_REVIEW"
    return "", "CATEGORY_UNRESOLVED"

if not DB.exists() or not STAGING.exists():
    raise FileNotFoundError("Required database or staging CSV is missing.")

with STAGING.open("r", encoding="utf-8-sig", newline="") as f:
    staged = list(csv.DictReader(f))

if not staged:
    raise ValueError("Staging CSV has no records.")

uri = DB.resolve().as_uri() + "?mode=ro"
with sqlite3.connect(uri, uri=True) as conn:
    conn.execute("PRAGMA query_only = ON")
    existing = conn.execute(
        "SELECT product_id, product_name, category FROM products"
    ).fetchall()
    existing_columns = {
        row[1] for row in conn.execute('PRAGMA table_info("products")')
    }

required_columns = {
    "product_id", "product_name", "category", "discounted_price_inr",
    "actual_price_inr", "discount_percentage", "rating", "rating_count",
    "about_product", "img_link", "product_link", "source_row_number",
    "source_rows_for_product"
}
if not required_columns.issubset(existing_columns):
    raise RuntimeError("Production schema differs from expected schema.")

existing_ids = {str(row[0]) for row in existing}
existing_names = {}
existing_categories = {row[2] for row in existing if row[2]}
for pid, name, category in existing:
    existing_names.setdefault(normalize(name), []).append(str(pid))

proposals = []
warnings = []

for item in staged:
    name = (item.get("product_name") or "").strip()
    url = (item.get("source_url") or "").strip()
    raw_price = (item.get("price_inr") or "").strip()

    try:
        price = float(raw_price)
        if not 0 < price < 10_000_000:
            price = None
    except ValueError:
        price = None

    pid = make_id(name)
    category, category_review = category_for(name)
    issues = [category_review]

    if not name:
        issues.append("MISSING_PRODUCT_NAME")
    if price is None:
        issues.append("INVALID_PRICE")
    if not url.startswith("https://"):
        issues.append("INVALID_SOURCE_URL")
    if normalize(name) in existing_names:
        issues.append("EXISTING_NAME_COLLISION")
    if pid in existing_ids:
        issues.append("GENERATED_ID_COLLISION")
    if category and category not in existing_categories:
        issues.append("CATEGORY_NOT_IN_PRODUCTION_DB")

    proposal = {
        "proposed_product_id": pid,
        "product_name": name,
        "proposed_category": category,
        "candidate_price_inr": price if price is not None else "",
        "actual_price_inr": "",
        "discounted_price_inr": "",
        "discount_percentage": "",
        "rating": "",
        "rating_count": "",
        "source_rating_mean_for_review": item.get("source_rating_mean", ""),
        "source_rating_count_for_review": item.get("source_rating_count", ""),
        "about_product": "",
        "img_link": "",
        "product_link": url,
        "source_dataset": item.get("source_dataset", ""),
        "source_platform": item.get("source_platform", ""),
        "redistribution_rights": item.get("redistribution_rights", ""),
        "category_review": category_review,
        "status": "REVIEW_REQUIRED" if issues else "READY_FOR_MANUAL_REVIEW",
        "issues": ";".join(issues),
    }
    proposals.append(proposal)

    for issue in issues:
        warnings.append({"product_name": name, "issue": issue})

csv_path = OUT / "flipkart_speakers_mapped_proposal.csv"
report_path = OUT / "flipkart_speakers_mapped_report.json"

if proposals:
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(proposals[0].keys()))
        writer.writeheader()
        writer.writerows(proposals)

report = {
    "staged_records": len(staged),
    "production_records_read": len(existing),
    "proposed_category_counts": {
        category: sum(p["proposed_category"] == category for p in proposals)
        for category in sorted({p["proposed_category"] for p in proposals})
    },
    "name_collisions": sum("EXISTING_NAME_COLLISION" in p["issues"] for p in proposals),
    "id_collisions": sum("GENERATED_ID_COLLISION" in p["issues"] for p in proposals),
    "valid_candidate_prices": sum(p["candidate_price_inr"] != "" for p in proposals),
    "ratings_written_to_production_fields": False,
    "production_database_modified": False,
    "redistribution_rights_verified": False,
    "database_import_performed": False,
    "warnings": warnings,
    "proposal_csv": str(csv_path),
}

report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

print(json.dumps(report, indent=2, ensure_ascii=False))
print("\nNo production database changes were made.")
