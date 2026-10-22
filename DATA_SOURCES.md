# ShopWise AI — Data Sources and Licensing

## 1. Amazon Sales Dataset

- **Dataset source:** [Amazon Sales Dataset — Kaggle](https://www.kaggle.com/datasets/karkavelrajaj/amazon-sales-dataset)
- **Dataset creator:** Karkavelraja J.
- **Stated license:** [Creative Commons Attribution–NonCommercial–ShareAlike 4.0 International (CC BY-NC-SA 4.0)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

### Modifications

The dataset is processed to select the Computers & Accessories category, consolidate repeated product identifiers, normalize price and rating fields, and generate product and review-source audit files.

The current local catalogue contains 375 unique product listings and 453 review-source records.

### Important limitations

- The dataset's license and any applicable upstream rights must be considered before redistribution or public deployment.
- Review boundaries have not been sufficiently verified to support reliable sentiment analysis.
- Prices, ratings, descriptions, and product links may be outdated or inaccurate.
- This project is not endorsed by Kaggle, the dataset creator, or Amazon.

## 2. Additional Data Sources

No supplementary product dataset has been integrated yet.

Any future source must be reviewed for license compatibility, attribution requirements, redistribution permissions, schema compatibility, and data quality before integration.

## 3. Project Data Policy

- Raw datasets, processed data files, and local SQLite databases are excluded from Git.
- Dataset attribution and processing changes should be documented.
- Public deployment must not imply that all underlying product content is cleared for redistribution.
- Product data must not be fabricated to increase catalogue size.

## 4. Project Code

The code in this repository is separate from the third-party product data. No license for the project code is implied by the dataset's license.
