# Testing & Quality Assurance Strategy

## Unit and Integration Tests

### 1. PySpark Transformation Testing
- Scope: Validation of schema casting, date parsing ISO-8601, and null filtering.
- Framework: `pytest` with local PySpark `SparkSession` context.

### 2. Data Quality Assertions
- Validate `star_rating` integer domain constraint: $1 \le \text{star\_rating} \le 5$.
- Validate `review_id` non-null constraint across all silver partitions.

### 3. JDBC Target Integration Testing
- Verify schema compatibility against Oracle dictionary tables (`USER_TAB_COLUMNS`).
