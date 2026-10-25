# ShopWise AI — Intelligent Shopping Assistant

ShopWise AI helps users discover products within their budget, compare options, and explore alternatives using explainable recommendations.

Built with Python, Streamlit, SQLite, Pandas, and scikit-learn, it combines TF-IDF text matching with product ratings to rank relevant products.

## Features

- **Product Search:** Search by keywords, budget, and minimum rating.
- **Product Comparison:** Compare selected products side by side.
- **Alternative Recommendations:** Explore similar products within a budget.
- **Explainable Results:** View prices, ratings, match scores, and recommendation reasons.
- **Product-Type Filtering:** Reduce irrelevant results for supported product queries.

## Tech Stack

Python · Streamlit · SQLite · Pandas · scikit-learn · TF-IDF · pytest

## Getting Started

### 1. Install dependencies

```bash
python -m pip install -r requirements.txt
```

### 2. Prepare the dataset

Obtain the source dataset from an authorized source and confirm its license permits your intended use.

Place the CSV file at:

`data/raw/amazon.csv`

The raw dataset, processed data, and SQLite database are excluded from Git. Prepare the data and build the database locally before launching the application.

### 3. Generate processed data

From the project root, run:

```bash
python src/cleaning/clean_dataset.py
```

This generates the processed product and review-audit files under `data/processed/`. It overwrites existing generated files, so back them up first if needed.

### 4. Build the database

```bash
python src/database/init_db.py
```

**Warning:** This script drops and recreates the existing `products` and `review_source_records` tables. Back up your current database before running it.

### 5. Verify the database

```bash
python src/database/verify_db.py
```

The verifier checks product and review-source counts, required fields, prices, ratings, duplicate IDs, and foreign-key integrity.

### 6. Launch the application

```bash
python -m streamlit run app.py
```

Open the local URL shown in the terminal.

## Run Tests

```bash
python -m pytest -q
```

The current test suite contains 64 automated tests. Run `python -m pytest -q` to verify the suite.

## Current Scope

The current catalogue contains 375 unique product listings across 57 stored category paths, primarily within Computers & Accessories. Coverage varies substantially by product type.

## Limitations

- Prices, ratings, and descriptions may be outdated or inaccurate.
- Live prices, stock availability, and product specifications are not verified.
- Search uses lexical TF-IDF matching, not semantic embeddings.
- Product-type filtering is rule-based and supports selected query types.
- Review boundaries have not been sufficiently verified for reliable sentiment analysis.
- Dataset licensing and redistribution permissions must be confirmed before publishing or deploying the dataset.

## Project Status

The local application supports product search, comparison, and alternative recommendations. The SQLite database is not committed to Git, so a deployment must provision a valid catalogue separately. Broader catalogue coverage, reproducible deployment, and public deployment remain future tasks.

---

Built to make product discovery and comparison simpler through explainable recommendations.