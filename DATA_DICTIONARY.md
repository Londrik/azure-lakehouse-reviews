# Data Dictionary: Lakehouse Metrics

## Bronze Layer (`s3a://lakehouse/bronze/amazon_reviews/books/data.tsv`)
- Schema: Schema-on-read (Text/TSV format).
- Ingestion Strategy: Full load raw append.

## Silver Layer (`s3a://lakehouse/silver/amazon_reviews/books/`)
| Field | Type | Constraint | Description |
| :--- | :--- | :--- | :--- |
| `review_id` | String | NOT NULL | Unique identifier of the review |
| `product_id` | String | NOT NULL | ASIN / Book ISBN identifier |
| `star_rating` | Integer | 1 to 5 | Product score assigned by customer |
| `helpful_votes`| Integer | $\ge 0$ | Community upvotes for the review |
| `total_votes` | Integer | $\ge 0$ | Total interaction votes on review |
| `review_date` | Date | ISO-8601 | Published date (`yyyy-MM-dd`) |
| `ingestion_timestamp` | Timestamp | Calculated | Ingestion audit control flag |

## Gold Layer (`Oracle DB -> GOLD_BOOK_REVIEWS`)
| Column Name | Oracle Type | Key | Description |
| :--- | :--- | :--- | :--- |
| `PRODUCT_ID` | VARCHAR2(12) | PK | Book ISBN / Unique product key |
| `PRODUCT_TITLE` | VARCHAR2(40) | - | Title of the book |
| `TOTAL_REVIEWS` | NUMBER | - | Aggregate count of valid reviews |
| `AVG_RATING` | NUMBER(3,2) | - | Mean star rating score |
| `AVG_HELPFUL_VOTES`| NUMBER(5,2) | - | Mean helpful community votes |
