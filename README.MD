# Integrated Data Engineering Learning Plan
## 12 Weeks | 1-2 Hours/Day | All Skills Together

**Core Philosophy:** Build one evolving project that grows in complexity each week. Learn Python, SQL, data structures, Spark, and Airflow together through realistic scenarios.

**The Project:** Build a production-ready CRM data platform for your business
- Week 1-4: Foundation (local development)
- Week 5-8: Scale & optimize (distributed processing)
- Week 9-12: Production (orchestration & deployment)

---

## PHASE 1: FOUNDATION (Weeks 1-4)
### Build: Basic CRM Data Pipeline

### Week 1: Setup & First Pipeline
**Goal:** Get a working end-to-end pipeline (CSV Ã¢â€ â€™ Python Ã¢â€ â€™ PostgreSQL)

#### Session 1.1 (90 min) - Environment Setup
**Concepts:** Docker, PostgreSQL, Python environment
**Tasks:**
- Install Docker Desktop
- Run PostgreSQL in Docker
- Install Python packages (psycopg2, pandas, sqlalchemy)
- Connect to PostgreSQL from Python

**Exercise:**
```python
# File: test_connection.py
import psycopg2

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="crm_dev",
    user="postgres",
    password="dev123"
)

# Test query
cursor = conn.cursor()
cursor.execute("SELECT version();")
print(cursor.fetchone())
conn.close()
```

**Success Criteria:** Successfully connect and query PostgreSQL

---

#### Session 1.2 (90 min) - First Table & Data Load
**Concepts:** SQL DDL, Python file I/O, basic OOP
**Tasks:**
- Design your first table (leads)
- Create CSV with sample data
- Write Python class to load CSV to PostgreSQL

**Exercise:**
```sql
-- File: schema.sql
CREATE TABLE leads (
    id SERIAL PRIMARY KEY,
    company_name VARCHAR(255) NOT NULL,
    contact_person VARCHAR(255),
    email VARCHAR(255),
    industry VARCHAR(100),
    status VARCHAR(50) DEFAULT 'New',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

```python
# File: data_loader.py
import csv
import psycopg2

class CSVLoader:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def load_csv(self, filepath, table_name):
        # TODO: Implement CSV reading and INSERT
        pass

    def close(self):
        self.conn.close()

# Test with sample CSV
loader = CSVLoader(db_config)
loader.load_csv('leads_sample.csv', 'leads')
loader.close()
```

**Challenge:** Load 100 sample leads from CSV to PostgreSQL

---

#### Session 1.3 (90 min) - Query & Transform
**Concepts:** SQL SELECT, Python data structures (lists, dicts)
**Tasks:**
- Write SQL queries to analyze leads
- Write Python function to export results to CSV

**Exercise:**
```sql
-- queries.sql
-- Q1: Count leads by status
SELECT status, COUNT(*) as count
FROM leads
GROUP BY status;

-- Q2: Recent leads (last 7 days)
SELECT * FROM leads
WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY created_at DESC;
```

```python
# File: query_runner.py
class QueryRunner:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def run_query(self, sql):
        """Execute query and return results as list of dicts"""
        # TODO: Implement
        pass

    def export_to_csv(self, sql, output_file):
        """Run query and save results to CSV"""
        # TODO: Implement
        pass

# Test
runner = QueryRunner(db_config)
results = runner.run_query("SELECT * FROM leads WHERE status = 'New'")
runner.export_to_csv("SELECT * FROM leads", "leads_export.csv")
```

**Challenge:** Create a daily report showing lead counts by status

---

#### Session 1.4 (120 min) - Data Validation
**Concepts:** Python conditionals, exceptions, SQL constraints
**Tasks:**
- Add validation before inserting data
- Handle duplicate emails
- Log validation errors

**Exercise:**
```python
# File: validator.py
class LeadValidator:
    def __init__(self):
        self.errors = []

    def validate_lead(self, lead_data):
        """
        Validate lead data before insert
        Rules:
        - Email must be valid format
        - Company name required
        - Status must be in allowed list
        """
        # TODO: Implement validation logic
        pass

    def is_valid(self):
        return len(self.errors) == 0

    def get_errors(self):
        return self.errors

# Update CSVLoader to use validator
class CSVLoader:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)
        self.validator = LeadValidator()

    def load_csv(self, filepath):
        with open(filepath) as f:
            reader = csv.DictReader(f)
            for row in reader:
                if self.validator.validate_lead(row):
                    # Insert to DB
                    pass
                else:
                    # Log errors
                    print(f"Invalid row: {self.validator.get_errors()}")
```

**Challenge:** Process a CSV with 20% invalid data, report all errors

---

#### Session 1.5 (90 min) - Week 1 Mini-Project
**Project:** Complete Basic ETL Pipeline
**Deliverables:**
1. PostgreSQL database with leads table
2. Python classes: CSVLoader, QueryRunner, LeadValidator
3. Sample data: 500 leads in CSV
4. Daily report script: generates CSV of lead counts
5. Error log: tracks all validation failures

**Integration Test:**
- Load 500 leads from CSV (with some invalid rows)
- Query database to verify data
- Generate daily report
- Review error logs

---

### Week 2: Expand Schema & Add Complexity
**Goal:** Multi-table database with relationships + data structures

#### Session 2.1 (90 min) - Relational Design
**Concepts:** Foreign keys, JOINs, hash tables
**Tasks:**
- Add companies and interactions tables
- Establish relationships
- Use Python dict for fast lookups

**Exercise:**
```sql
-- schema_v2.sql
CREATE TABLE companies (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    industry VARCHAR(100),
    website VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE interactions (
    id SERIAL PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    interaction_type VARCHAR(50), -- email, call, meeting
    notes TEXT,
    interaction_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Update leads to reference companies
ALTER TABLE leads ADD COLUMN company_id INTEGER REFERENCES companies(id);
```

```python
# File: deduplicator.py
class CompanyDeduplicator:
    def __init__(self):
        self.seen_companies = {}  # Hash table: name -> id

    def get_or_create_company(self, company_name):
        """
        Check if company exists in hash table
        If not, create in DB and add to hash table
        Return company_id
        """
        # TODO: Implement using hash table for O(1) lookups
        pass

# Usage in CSVLoader
loader = CSVLoader(db_config)
dedup = CompanyDeduplicator()

for row in csv_data:
    company_id = dedup.get_or_create_company(row['company_name'])
    # Insert lead with company_id
```

**Challenge:** Load 1000 leads, deduplicate companies (should be ~200 unique)

---

#### Session 2.2 (120 min) - Complex Queries
**Concepts:** JOINs, subqueries, GROUP BY, window functions
**Tasks:**
- Query across multiple tables
- Calculate aggregates
- Rank data

**Exercise:**
```sql
-- analytics.sql

-- Q1: Leads with interaction count
SELECT
    l.company_name,
    l.status,
    COUNT(i.id) as interaction_count
FROM leads l
LEFT JOIN interactions i ON l.id = i.lead_id
GROUP BY l.id, l.company_name, l.status
ORDER BY interaction_count DESC;

-- Q2: Most active companies (last 30 days)
SELECT
    c.name,
    COUNT(i.id) as recent_interactions
FROM companies c
JOIN leads l ON c.id = l.company_id
JOIN interactions i ON l.id = i.lead_id
WHERE i.interaction_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.id, c.name
ORDER BY recent_interactions DESC
LIMIT 10;

-- Q3: Conversion funnel
SELECT
    status,
    COUNT(*) as count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 2) as percentage
FROM leads
GROUP BY status
ORDER BY count DESC;
```

**Python Integration:**
```python
# File: analytics.py
class CRMAnalytics:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def get_lead_funnel(self):
        """Return lead counts by status"""
        # TODO: Execute funnel query
        pass

    def get_top_companies(self, days=30, limit=10):
        """Return most active companies"""
        # TODO: Execute query with parameters
        pass

    def export_dashboard_data(self, output_dir):
        """Export all analytics to JSON files for dashboard"""
        # TODO: Run multiple queries, save as JSON
        pass
```

**Challenge:** Generate JSON files with all analytics data

---

#### Session 2.3 (90 min) - Memory-Efficient Processing
**Concepts:** Generators, streaming, chunking
**Tasks:**
- Process large CSV without loading all into memory
- Use generators for data pipeline

**Exercise:**
```python
# File: streaming_loader.py
def read_csv_in_chunks(filepath, chunk_size=1000):
    """
    Generator that yields chunks of CSV data
    Memory efficient for large files
    """
    with open(filepath) as f:
        reader = csv.DictReader(f)
        chunk = []
        for row in reader:
            chunk.append(row)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        if chunk:  # Don't forget last chunk
            yield chunk

class StreamingLoader:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def load_large_csv(self, filepath):
        """Process CSV in chunks to handle large files"""
        total_processed = 0
        total_errors = 0

        for chunk in read_csv_in_chunks(filepath, chunk_size=1000):
            # Process chunk
            # Batch insert to DB
            total_processed += len(chunk)
            print(f"Processed {total_processed} rows...")

        return total_processed, total_errors

# Test with 100k row CSV
loader = StreamingLoader(db_config)
processed, errors = loader.load_large_csv('large_leads.csv')
print(f"Loaded {processed} rows with {errors} errors")
```

**Challenge:** Load a 100MB CSV file without running out of memory

---

#### Session 2.4 (120 min) - Data Structures Applied
**Concepts:** Sets, queues, stacks
**Tasks:**
- Use sets for deduplication
- Implement job queue for async processing
- Track processing state

**Exercise:**
```python
# File: job_queue.py
from collections import deque
from datetime import datetime

class Job:
    def __init__(self, job_id, data):
        self.id = job_id
        self.data = data
        self.created_at = datetime.now()
        self.status = 'pending'

class JobQueue:
    def __init__(self):
        self.queue = deque()  # FIFO queue
        self.processing = {}  # Currently processing: {job_id: job}
        self.completed = set()  # Completed job IDs
        self.failed = []  # Failed jobs stack

    def add_job(self, job):
        """Add job to queue"""
        self.queue.append(job)

    def get_next_job(self):
        """Pop next job from queue"""
        if not self.queue:
            return None
        job = self.queue.popleft()
        self.processing[job.id] = job
        return job

    def mark_complete(self, job_id):
        """Mark job as successfully completed"""
        if job_id in self.processing:
            del self.processing[job_id]
            self.completed.add(job_id)

    def mark_failed(self, job_id, error):
        """Mark job as failed"""
        if job_id in self.processing:
            job = self.processing[job_id]
            job.status = 'failed'
            job.error = error
            self.failed.append(job)
            del self.processing[job_id]

    def get_status(self):
        """Return queue statistics"""
        return {
            'pending': len(self.queue),
            'processing': len(self.processing),
            'completed': len(self.completed),
            'failed': len(self.failed)
        }

# Usage: Queue CSV processing jobs
queue = JobQueue()

# Add jobs for each CSV file
for filepath in csv_files:
    job = Job(job_id=filepath, data={'filepath': filepath})
    queue.add_job(job)

# Process queue
while True:
    job = queue.get_next_job()
    if not job:
        break

    try:
        # Process the CSV
        load_csv(job.data['filepath'])
        queue.mark_complete(job.id)
    except Exception as e:
        queue.mark_failed(job.id, str(e))

print(queue.get_status())
```

**Challenge:** Process 10 CSV files using job queue, handle 2 failures

---

#### Session 2.5 (90 min) - Introduction to Testing with pytest
**Concepts:** Unit tests, test-driven development, pytest basics, assertions
**Tasks:**
- Install and setup pytest
- Write unit tests for CSVLoader and QueryRunner classes
- Learn test structure (arrange, act, assert)
- Run tests and interpret results

**Exercise:**
```python
# File: test_data_loader.py
import pytest
import psycopg2
from data_loader import CSVLoader

@pytest.fixture
def db_config():
    """Fixture provides test database config"""
    return {
        "host": "localhost",
        "database": "crm_dev",
        "user": "postgres",
        "password": "dev123"
    }

@pytest.fixture
def loader(db_config):
    """Fixture creates CSVLoader instance"""
    loader = CSVLoader(db_config)
    yield loader  # Provide to test
    loader.close()  # Cleanup after test

def test_connection(loader):
    """Test that CSVLoader connects successfully"""
    assert loader.conn is not None
    assert loader.cursor is not None

def test_get_row_count(loader):
    """Test row count method returns integer"""
    count = loader.get_row_count('leads')
    assert isinstance(count, int)
    assert count >= 0

def test_clear_table(loader):
    """Test clearing table removes all rows"""
    # Arrange: ensure some data exists
    initial_count = loader.get_row_count('leads')

    # Act: clear the table
    loader.clear_table('leads')

    # Assert: table should be empty
    final_count = loader.get_row_count('leads')
    assert final_count == 0
```

```python
# File: test_query_runner.py
import pytest
from query_runner import QueryRunner

def test_run_query_returns_list(db_config):
    """Test that run_query returns a list"""
    runner = QueryRunner(db_config)
    results = runner.run_query("SELECT * FROM leads LIMIT 5")

    assert isinstance(results, list)
    runner.close()

def test_export_to_csv_creates_file(db_config, tmp_path):
    """Test CSV export creates file"""
    runner = QueryRunner(db_config)
    output_file = tmp_path / "test_export.csv"

    runner.export_to_csv(
        "SELECT * FROM leads LIMIT 10",
        str(output_file)
    )

    assert output_file.exists()
    runner.close()
```

**Running tests:**
```bash
# Install pytest
uv pip install pytest

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest test_data_loader.py
```

**Challenge:** Write 5 more tests covering edge cases:
- Test loading empty CSV
- Test invalid database connection
- Test query with no results
- Test export with special characters in data
- Test connection cleanup

---

### Week 2 Mini-Project
**Project:** Multi-Table ETL with Analytics & Tests
**Deliverables:**
1. Expanded schema: leads, companies, interactions
2. Deduplication using hash tables
3. Job queue for processing multiple files
4. Analytics module with 5 queries
5. JSON export for dashboard
6. **Test suite with 10+ tests covering all classes**

**Integration Test:**
- Load 5 CSV files via job queue (5000 total leads)
- Deduplicate companies
- Add 1000 interactions
- Generate analytics JSON files
- Verify all relationships are correct
- **All tests pass with pytest**

---

### Week 3: Scale & Optimize
**Goal:** Handle larger data, optimize queries, introduce Spark

#### Session 3.1 (120 min) - Query Performance
**Concepts:** Indexes, EXPLAIN ANALYZE, query optimization
**Tasks:**
- Identify slow queries
- Add appropriate indexes
- Measure improvement

**Exercise:**
```sql
-- performance_test.sql

-- Slow query (no index)
EXPLAIN ANALYZE
SELECT * FROM leads WHERE email = 'test@example.com';

-- Add index
CREATE INDEX idx_leads_email ON leads(email);

-- Fast query (with index)
EXPLAIN ANALYZE
SELECT * FROM leads WHERE email = 'test@example.com';

-- Compound index for common query pattern
CREATE INDEX idx_leads_status_created ON leads(status, created_at DESC);

-- Query that benefits from compound index
EXPLAIN ANALYZE
SELECT * FROM leads
WHERE status = 'New'
ORDER BY created_at DESC
LIMIT 100;
```

```python
# File: performance_monitor.py
import time

class QueryPerformanceMonitor:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def measure_query(self, sql, params=None):
        """Execute query and measure time"""
        cursor = self.conn.cursor()

        start = time.time()
        cursor.execute(sql, params)
        results = cursor.fetchall()
        elapsed = time.time() - start

        return {
            'rows': len(results),
            'time_ms': elapsed * 1000,
            'query': sql
        }

    def benchmark_queries(self, queries):
        """Run multiple queries and compare performance"""
        results = []
        for name, sql in queries.items():
            result = self.measure_query(sql)
            result['name'] = name
            results.append(result)
        return results

# Test queries before/after indexing
monitor = QueryPerformanceMonitor(db_config)
queries = {
    'find_by_email': "SELECT * FROM leads WHERE email = 'test@example.com'",
    'recent_leads': "SELECT * FROM leads WHERE created_at >= CURRENT_DATE - 7",
    'leads_by_status': "SELECT * FROM leads WHERE status = 'New' ORDER BY created_at DESC"
}

results = monitor.benchmark_queries(queries)
for r in results:
    print(f"{r['name']}: {r['time_ms']:.2f}ms ({r['rows']} rows)")
```

**Challenge:** Optimize 5 slow queries, achieve <50ms execution time

---

#### Session 3.2 (120 min) - Introduction to Spark
**Concepts:** Distributed computing, Spark basics, DataFrames
**Tasks:**
- Install PySpark
- Read CSV with Spark
- Compare with Pandas

**Exercise:**
```python
# File: spark_intro.py
from pyspark.sql import SparkSession
import pandas as pd
import time

# Create Spark session
spark = SparkSession.builder \
    .appName("CRM Analytics") \
    .master("local[*]") \
    .getOrCreate()

# Read CSV with Spark
spark_df = spark.read.csv('leads.csv', header=True, inferSchema=True)

# Basic operations
spark_df.show(10)
spark_df.printSchema()
spark_df.describe().show()

# Filter and aggregate
result = spark_df.filter(spark_df['status'] == 'New') \
                 .groupBy('industry') \
                 .count() \
                 .orderBy('count', ascending=False)
result.show()

# Compare with Pandas
def process_with_pandas(filepath):
    start = time.time()
    df = pd.read_csv(filepath)
    result = df[df['status'] == 'New'].groupby('industry').size()
    elapsed = time.time() - start
    return elapsed

def process_with_spark(filepath):
    start = time.time()
    df = spark.read.csv(filepath, header=True, inferSchema=True)
    result = df.filter(df['status'] == 'New') \
               .groupBy('industry') \
               .count()
    result.collect()  # Force execution
    elapsed = time.time() - start
    return elapsed

# Benchmark on different file sizes
for size in ['1MB', '10MB', '100MB']:
    pandas_time = process_with_pandas(f'leads_{size}.csv')
    spark_time = process_with_spark(f'leads_{size}.csv')
    print(f"{size}: Pandas={pandas_time:.2f}s, Spark={spark_time:.2f}s")
```

**Challenge:** Determine at what file size Spark becomes faster than Pandas

---

#### Session 3.3 (90 min) - Spark Transformations
**Concepts:** Map, filter, groupBy, aggregations
**Tasks:**
- Clean data with Spark
- Perform aggregations
- Write output in partitions

**Exercise:**
```python
# File: spark_etl.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, sum, avg, when, trim, lower

spark = SparkSession.builder.appName("CRM ETL").getOrCreate()

# Read data
df = spark.read.csv('leads.csv', header=True, inferSchema=True)

# Data cleaning transformations
cleaned = df \
    .withColumn('email', trim(lower(col('email')))) \
    .withColumn('company_name', trim(col('company_name'))) \
    .filter(col('email').isNotNull()) \
    .filter(col('company_name').isNotNull()) \
    .dropDuplicates(['email'])

# Add derived column
enriched = cleaned.withColumn(
    'priority',
    when(col('industry') == 'Technology', 'High')
    .when(col('industry') == 'Healthcare', 'High')
    .otherwise('Medium')
)

# Aggregate by industry
industry_stats = enriched.groupBy('industry') \
    .agg(
        count('*').alias('lead_count'),
        count(when(col('status') == 'Converted', 1)).alias('converted_count')
    )

# Calculate conversion rate
from pyspark.sql.functions import round as spark_round
industry_stats = industry_stats.withColumn(
    'conversion_rate',
    spark_round((col('converted_count') / col('lead_count')) * 100, 2)
)

# Write results partitioned by industry
enriched.write \
    .partitionBy('industry') \
    .mode('overwrite') \
    .parquet('output/leads_by_industry')

# Write aggregates
industry_stats.write \
    .mode('overwrite') \
    .parquet('output/industry_stats')

spark.stop()
```

**Challenge:** Clean and aggregate 1M lead records using Spark

---

#### Session 3.4 (120 min) - Spark + PostgreSQL Integration
**Concepts:** JDBC connections, reading/writing to databases
**Tasks:**
- Read from PostgreSQL with Spark
- Process with Spark
- Write back to PostgreSQL

**Exercise:**
```python
# File: spark_postgres.py
from pyspark.sql import SparkSession

# Create Spark session with PostgreSQL JDBC driver
spark = SparkSession.builder \
    .appName("CRM ETL") \
    .config("spark.jars", "postgresql-42.2.23.jar") \
    .getOrCreate()

# JDBC connection properties
jdbc_url = "jdbc:postgresql://localhost:5432/crm_dev"
connection_properties = {
    "user": "postgres",
    "password": "dev123",
    "driver": "org.postgresql.Driver"
}

# Read from PostgreSQL
leads_df = spark.read.jdbc(
    url=jdbc_url,
    table="leads",
    properties=connection_properties
)

interactions_df = spark.read.jdbc(
    url=jdbc_url,
    table="interactions",
    properties=connection_properties
)

# Join and aggregate
from pyspark.sql.functions import col, count

lead_summary = leads_df.alias('l') \
    .join(interactions_df.alias('i'), col('l.id') == col('i.lead_id'), 'left') \
    .groupBy('l.id', 'l.company_name', 'l.status') \
    .agg(count('i.id').alias('interaction_count')) \
    .filter(col('interaction_count') > 0)

# Write results back to PostgreSQL (new table)
lead_summary.write.jdbc(
    url=jdbc_url,
    table="lead_engagement_summary",
    mode="overwrite",
    properties=connection_properties
)

# Create materialized view equivalent
high_value_leads = leads_df \
    .filter(col('status').isin(['Qualified', 'Proposal Sent'])) \
    .filter(col('industry').isin(['Technology', 'Healthcare']))

high_value_leads.write.jdbc(
    url=jdbc_url,
    table="high_value_leads_cache",
    mode="overwrite",
    properties=connection_properties
)

spark.stop()
```

**Challenge:** Process 500k leads from PostgreSQL with Spark, create summary tables

---

#### Session 3.5 (90 min) - Week 3 Mini-Project
**Project:** Spark-Powered Analytics Pipeline
**Deliverables:**
1. Spark ETL script that reads from PostgreSQL
2. Data cleaning and enrichment
3. Aggregations by multiple dimensions
4. Write results back to PostgreSQL
5. Performance comparison: Pandas vs Spark on 1M records

**Integration Test:**
- Load 1M leads into PostgreSQL
- Process with Spark
- Create 5 summary tables
- Query summary tables from Python
- Generate final reports

---

### Week 4: Orchestration Basics
**Goal:** Introduce Airflow, schedule pipelines

#### Session 4.1 (120 min) - Airflow Setup
**Concepts:** DAGs, tasks, scheduling
**Tasks:**
- Install Airflow with Docker
- Create first DAG
- Run manually

**Exercise:**
```python
# File: dags/first_dag.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def extract_leads():
    """Extract new leads from source"""
    print("Extracting leads...")
    # Your extraction logic
    return "Extracted 100 leads"

def load_to_db():
    """Load leads to PostgreSQL"""
    print("Loading to database...")
    # Your load logic
    return "Loaded successfully"

dag = DAG(
    'simple_etl',
    default_args=default_args,
    description='Simple ETL pipeline',
    schedule_interval='@daily',
    catchup=False
)

extract_task = PythonOperator(
    task_id='extract',
    python_callable=extract_leads,
    dag=dag
)

load_task = PythonOperator(
    task_id='load',
    python_callable=load_to_db,
    dag=dag
)

extract_task >> load_task
```

**Challenge:** Create working Airflow DAG that runs your CSV loader

---

#### Session 4.2 (90 min) - Complex DAG Patterns
**Concepts:** Task dependencies, parallel execution, XComs
**Tasks:**
- Create DAG with parallel tasks
- Pass data between tasks
- Handle task failures

**Exercise:**
```python
# File: dags/parallel_etl.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime

def extract_from_source(source_name, **context):
    """Extract from different sources in parallel"""
    print(f"Extracting from {source_name}")
    data = f"Data from {source_name}"

    # Push to XCom for downstream tasks
    context['task_instance'].xcom_push(key='data', value=data)
    return data

def transform_data(source_name, **context):
    """Transform data from specific source"""
    # Pull data from XCom
    data = context['task_instance'].xcom_pull(
        task_ids=f'extract_{source_name}',
        key='data'
    )

    print(f"Transforming: {data}")
    transformed = f"Cleaned {data}"
    context['task_instance'].xcom_push(key='transformed', value=transformed)
    return transformed

def merge_and_load(**context):
    """Merge all transformed data and load"""
    source1 = context['task_instance'].xcom_pull(
        task_ids='transform_api1',
        key='transformed'
    )
    source2 = context['task_instance'].xcom_pull(
        task_ids='transform_api2',
        key='transformed'
    )
    source3 = context['task_instance'].xcom_pull(
        task_ids='transform_csv',
        key='transformed'
    )

    print(f"Merging: {source1}, {source2}, {source3}")
    # Load to database
    return "Loaded all sources"

with DAG(
    'parallel_multi_source_etl',
    start_date=datetime(2025, 12, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    # Extract tasks (run in parallel)
    extract_api1 = PythonOperator(
        task_id='extract_api1',
        python_callable=extract_from_source,
        op_kwargs={'source_name': 'api1'}
    )

    extract_api2 = PythonOperator(
        task_id='extract_api2',
        python_callable=extract_from_source,
        op_kwargs={'source_name': 'api2'}
    )

    extract_csv = PythonOperator(
        task_id='extract_csv',
        python_callable=extract_from_source,
        op_kwargs={'source_name': 'csv'}
    )

    # Transform tasks (run in parallel after extracts)
    transform_api1 = PythonOperator(
        task_id='transform_api1',
        python_callable=transform_data,
        op_kwargs={'source_name': 'api1'}
    )

    transform_api2 = PythonOperator(
        task_id='transform_api2',
        python_callable=transform_data,
        op_kwargs={'source_name': 'api2'}
    )

    transform_csv = PythonOperator(
        task_id='transform_csv',
        python_callable=transform_data,
        op_kwargs={'source_name': 'csv'}
    )

    # Load task (runs after all transforms)
    load = PythonOperator(
        task_id='load',
        python_callable=merge_and_load
    )

    # Set dependencies
    extract_api1 >> transform_api1
    extract_api2 >> transform_api2
    extract_csv >> transform_csv

    [transform_api1, transform_api2, transform_csv] >> load
```

**Challenge:** Build DAG that processes 3 sources in parallel

---

#### Session 4.3 (120 min) - Error Handling & Monitoring
**Concepts:** Retries, alerts, logging
**Tasks:**
- Add retry logic
- Implement error notifications
- Add detailed logging

**Exercise:**
```python
# File: dags/robust_etl.py
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.exceptions import AirflowException
from datetime import datetime, timedelta
import logging

# Configure logger
logger = logging.getLogger(__name__)

def send_alert(message):
    """Send alert on failure (could be Slack, email, etc.)"""
    logger.error(f"ALERT: {message}")
    # In production: send to Slack, PagerDuty, etc.

def extract_with_retry(**context):
    """Extract with error handling"""
    try:
        logger.info("Starting extraction...")

        # Simulate API call that might fail
        # Your actual extraction logic here

        logger.info("Extraction completed successfully")
        return {"status": "success", "rows": 1000}

    except Exception as e:
        error_msg = f"Extraction failed: {str(e)}"
        logger.error(error_msg)
        send_alert(error_msg)
        raise AirflowException(error_msg)

def validate_data(**context):
    """Validate data quality before loading"""
    data = context['task_instance'].xcom_pull(task_ids='extract')

    if not data or data.get('rows', 0) == 0:
        error_msg = "Validation failed: No data extracted"
        logger.error(error_msg)
        send_alert(error_msg)
        raise AirflowException(error_msg)

    if data['rows'] < 100:
        logger.warning(f"Low data volume: {data['rows']} rows")

    logger.info(f"Validation passed: {data['rows']} rows")
    return data

def load_with_transaction(**context):
    """Load data with transaction rollback on failure"""
    data = context['task_instance'].xcom_pull(task_ids='validate')

    try:
        logger.info("Starting load...")
        # BEGIN TRANSACTION
        # INSERT data
        # COMMIT
        logger.info(f"Loaded {data['rows']} rows successfully")

    except Exception as e:
        logger.error(f"Load failed: {str(e)}")
        # ROLLBACK
        send_alert(f"Load failed, transaction rolled back: {str(e)}")
        raise

default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'start_date': datetime(2025, 12, 1),
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
}

with DAG(
    'robust_etl_with_monitoring',
    default_args=default_args,
    schedule_interval='0 6 * * *',  # 6 AM daily
    catchup=False
) as dag:

    extract = PythonOperator(
        task_id='extract',
        python_callable=extract_with_retry
    )

    validate = PythonOperator(
        task_id='validate',
        python_callable=validate_data
    )

    load = PythonOperator(
        task_id='load',
        python_callable=load_with_transaction
    )

    extract >> validate >> load
```

**Challenge:** Add error handling to all your existing DAGs

---

#### Session 4.4 (90 min) - Scheduling & Backfills
**Concepts:** Cron expressions, execution dates, catchup
**Tasks:**
- Understand scheduling parameters
- Run backfills for historical data
- Handle daily vs hourly schedules

**Exercise:**
```python
# File: dags/scheduled_pipelines.py

# Daily at 6 AM
dag_daily = DAG(
    'daily_lead_report',
    schedule_interval='0 6 * * *',
    start_date=datetime(2025, 12, 1),
    catchup=False  # Don't backfill
)

# Every hour
dag_hourly = DAG(
    'hourly_webhook_processor',
    schedule_interval='0 * * * *',
    start_date=datetime(2025, 12, 1),
    catchup=False
)

# Every Monday at 8 AM
dag_weekly = DAG(
    'weekly_analytics_report',
    schedule_interval='0 8 * * 1',
    start_date=datetime(2025, 12, 1),
    catchup=False
)

# First of every month
dag_monthly = DAG(
    'monthly_data_cleanup',
    schedule_interval='0 0 1 * *',
    start_date=datetime(2025, 12, 1),
    catchup=False
)

def process_for_date(**context):
    """Process data for specific execution date"""
    execution_date = context['execution_date']
    logger.info(f"Processing data for {execution_date}")

    # Query data for this specific date
    # This makes backfills work correctly

# Backfill command (run in terminal):
# airflow dags backfill daily_lead_report \
#   --start-date 2025-11-01 \
#   --end-date 2025-11-30
```

**Challenge:** Create 4 DAGs with different schedules, test backfill

---

#### Session 4.5 (120 min) - Week 4 Mini-Project
**Project:** Complete Orchestrated Pipeline
**Deliverables:**
1. 3 Airflow DAGs:
   - Daily ETL (CSV Ã¢â€ â€™ PostgreSQL)
   - Weekly analytics (PostgreSQL Ã¢â€ â€™ Reports)
   - Hourly webhook processor
2. Error handling and retries on all tasks
3. Logging and monitoring
4. Successfully run all DAGs
5. Generate weekly report automatically

**Integration Test:**
- Deploy all DAGs to Airflow
- Trigger daily ETL manually
- Wait for weekly report DAG to run
- Verify data in PostgreSQL
- Check Airflow UI for task statuses

---

## PHASE 2: SCALE & OPTIMIZE (Weeks 5-8)
### Build: Distributed Processing & Advanced Analytics

### Week 5: Advanced Spark
**Goal:** Master Spark for large-scale data processing

#### Session 5.1 (120 min) - Spark Optimization
**Concepts:** Partitions, broadcast joins, caching
**Tasks:**
- Optimize Spark jobs
- Reduce shuffle operations
- Cache reused DataFrames

**Exercise:**
```python
# File: spark_optimization.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *

spark = SparkSession.builder \
    .appName("Optimized ETL") \
    .config("spark.sql.adaptive.enabled", "true") \
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
    .getOrCreate()

# Read data
leads = spark.read.parquet("leads.parquet")
interactions = spark.read.parquet("interactions.parquet")

# Check initial partitions
print(f"Leads partitions: {leads.rdd.getNumPartitions()}")

# Optimize partitioning (repartition for better parallelism)
leads_opt = leads.repartition(10, "company_id")

# Cache frequently used DataFrames
leads_opt.cache()

# Broadcast small lookup table
companies = spark.read.parquet("companies.parquet")
companies_broadcast = broadcast(companies)

# Join with broadcast (avoids shuffle)
enriched = leads_opt.join(companies_broadcast, "company_id")

# Persist intermediate results
enriched.persist()

# Multiple operations on same DataFrame
by_industry = enriched.groupBy("industry").count()
by_status = enriched.groupBy("status").count()

# Coalesce to reduce output files
final = enriched.coalesce(5)
final.write.mode("overwrite").parquet("output/enriched_leads")

spark.stop()
```

**Challenge:** Optimize Spark job to run 3x faster on 10M records

---

#### Session 5.2 (90 min) - Spark SQL & Temp Views
**Concepts:** Spark SQL, temp views, SQL vs DataFrame API
**Tasks:**
- Use SQL syntax with Spark
- Create temp views
- Compare performance

**Exercise:**
```python
# File: spark_sql.py
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("Spark SQL").getOrCreate()

# Read data
leads = spark.read.parquet("leads.parquet")
interactions = spark.read.parquet("interactions.parquet")

# Create temp views
leads.createOrReplaceTempView("leads")
interactions.createOrReplaceTempView("interactions")

# Write SQL queries
lead_summary = spark.sql("""
    SELECT
        l.company_name,
        l.status,
        l.industry,
        COUNT(i.id) as interaction_count,
        MAX(i.interaction_date) as last_interaction
    FROM leads l
    LEFT JOIN interactions i ON l.id = i.lead_id
    GROUP BY l.company_name, l.status, l.industry
    HAVING COUNT(i.id) > 5
    ORDER BY interaction_count DESC
""")

# Window functions in Spark SQL
ranked_leads = spark.sql("""
    SELECT
        company_name,
        status,
        interaction_count,
        RANK() OVER (PARTITION BY status ORDER BY interaction_count DESC) as rank
    FROM (
        SELECT
            l.company_name,
            l.status,
            COUNT(i.id) as interaction_count
        FROM leads l
        LEFT JOIN interactions i ON l.id = i.lead_id
        GROUP BY l.company_name, l.status
    )
    WHERE rank <= 10
""")

# Complex analytics query
conversion_funnel = spark.sql("""
    WITH lead_stages AS (
        SELECT
            id,
            company_name,
            status,
            created_at,
            LAG(status) OVER (PARTITION BY id ORDER BY created_at) as prev_status,
            LEAD(status) OVER (PARTITION BY id ORDER BY created_at) as next_status
        FROM leads
    )
    SELECT
        prev_status,
        status,
        COUNT(*) as transition_count
    FROM lead_stages
    WHERE prev_status IS NOT NULL
    GROUP BY prev_status, status
    ORDER BY transition_count DESC
""")

lead_summary.show()
ranked_leads.show()
conversion_funnel.show()

spark.stop()
```

**Challenge:** Rewrite 5 PostgreSQL queries using Spark SQL

---

#### Session 5.3 (120 min) - Spark Streaming Basics
**Concepts:** Micro-batches, structured streaming, windowing
**Tasks:**
- Process streaming data
- Implement sliding windows
- Write to sink continuously

**Exercise:**
```python
# File: spark_streaming.py
from pyspark.sql import SparkSession
from pyspark.sql.functions import *
from pyspark.sql.types import *

spark = SparkSession.builder \
    .appName("Streaming ETL") \
    .getOrCreate()

# Define schema for incoming data
schema = StructType([
    StructField("lead_id", IntegerType()),
    StructField("event_type", StringType()),
    StructField("timestamp", TimestampType()),
    StructField("data", StringType())
])

# Read streaming data from directory
streaming_df = spark.readStream \
    .schema(schema) \
    .json("streaming_input/")

# Add processing time
processed = streaming_df \
    .withColumn("processing_time", current_timestamp())

# Windowed aggregation (5-minute windows)
windowed_counts = processed \
    .withWatermark("timestamp", "10 minutes") \
    .groupBy(
        window("timestamp", "5 minutes", "1 minute"),
        "event_type"
    ) \
    .count()

# Write stream to output
query = windowed_counts \
    .writeStream \
    .outputMode("update") \
    .format("parquet") \
    .option("path", "streaming_output/") \
    .option("checkpointLocation", "checkpoints/") \
    .trigger(processingTime="30 seconds") \
    .start()

query.awaitTermination()
```

**Challenge:** Build streaming pipeline for real-time webhook processing

---

#### Session 5.4 (90 min) - PySpark + Airflow Integration
**Concepts:** SparkSubmitOperator, cluster vs local mode
**Tasks:**
- Run Spark jobs from Airflow
- Pass parameters to Spark jobs
- Monitor Spark job status

**Exercise:**
```python
# File: dags/spark_etl_dag.py
from airflow import DAG
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from datetime import datetime

def prepare_spark_config(**context):
    """Prepare configuration for Spark job"""
    execution_date = context['execution_date']
    config = {
        'input_path': f's3://data/leads/{execution_date.strftime("%Y-%m-%d")}/',
        'output_path': f's3://processed/leads/{execution_date.strftime("%Y-%m-%d")}/',
        'num_partitions': 10
    }
    return config

with DAG(
    'spark_etl_pipeline',
    start_date=datetime(2025, 12, 1),
    schedule_interval='@daily',
    catchup=False
) as dag:

    prepare_config = PythonOperator(
        task_id='prepare_config',
        python_callable=prepare_spark_config
    )

    spark_job = SparkSubmitOperator(
        task_id='process_leads_spark',
        application='/path/to/spark_etl.py',
        conn_id='spark_default',
        conf={
            'spark.executor.memory': '4g',
            'spark.executor.cores': '2',
            'spark.sql.adaptive.enabled': 'true'
        },
        application_args=[
            '--input', '{{ ti.xcom_pull(task_ids="prepare_config")["input_path"] }}',
            '--output', '{{ ti.xcom_pull(task_ids="prepare_config")["output_path"] }}'
        ]
    )

    prepare_config >> spark_job
```

**Challenge:** Create Airflow DAG that orchestrates 3 Spark jobs

---

#### Session 5.5 (120 min) - Week 5 Mini-Project
**Project:** Large-Scale Spark Pipeline
**Deliverables:**
1. Spark job processing 10M+ records
2. Optimized with partitioning and caching
3. Both batch and streaming versions
4. Orchestrated by Airflow
5. Results written to PostgreSQL and Parquet

**Integration Test:**
- Generate 10M synthetic lead records
- Process with optimized Spark job
- Measure processing time
- Verify output data quality
- Run from Airflow automatically

---

### Week 6: Data Warehouse & Analytics
**Goal:** Build production data warehouse

#### Session 6.1 (120 min) - Star Schema Design
**Concepts:** Fact tables, dimension tables, slowly changing dimensions
**Tasks:**
- Design star schema for CRM
- Implement SCD Type 2
- Create surrogate keys

**Exercise:**
```sql
-- File: warehouse_schema.sql

-- Dimension: Date
CREATE TABLE dim_date (
    date_key INTEGER PRIMARY KEY,
    date DATE NOT NULL,
    year INTEGER,
    quarter INTEGER,
    month INTEGER,
    month_name VARCHAR(20),
    week INTEGER,
    day_of_week INTEGER,
    day_name VARCHAR(20),
    is_weekend BOOLEAN,
    is_holiday BOOLEAN
);

-- Dimension: Lead (SCD Type 2)
CREATE TABLE dim_lead (
    lead_key SERIAL PRIMARY KEY,  -- Surrogate key
    lead_id INTEGER NOT NULL,      -- Natural key
    company_name VARCHAR(255),
    industry VARCHAR(100),
    status VARCHAR(50),

    -- SCD Type 2 fields
    valid_from DATE NOT NULL,
    valid_to DATE,
    is_current BOOLEAN DEFAULT TRUE,

    UNIQUE (lead_id, valid_from)
);

-- Dimension: Company
CREATE TABLE dim_company (
    company_key SERIAL PRIMARY KEY,
    company_id INTEGER NOT NULL,
    company_name VARCHAR(255),
    industry VARCHAR(100),
    website VARCHAR(255),

    valid_from DATE NOT NULL,
    valid_to DATE,
    is_current BOOLEAN DEFAULT TRUE
);

-- Fact: Interactions
CREATE TABLE fact_interactions (
    interaction_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    lead_key INTEGER REFERENCES dim_lead(lead_key),
    company_key INTEGER REFERENCES dim_company(company_key),

    interaction_type VARCHAR(50),
    duration_minutes INTEGER,
    outcome VARCHAR(100),

    -- Metrics
    meeting_scheduled BOOLEAN,
    proposal_sent BOOLEAN,
    converted BOOLEAN,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact: Daily Lead Snapshot
CREATE TABLE fact_daily_leads (
    snapshot_key BIGSERIAL PRIMARY KEY,
    date_key INTEGER REFERENCES dim_date(date_key),
    lead_key INTEGER REFERENCES dim_lead(lead_key),
    company_key INTEGER REFERENCES dim_company(company_key),

    status VARCHAR(50),
    days_in_status INTEGER,
    total_interactions INTEGER,
    last_interaction_days_ago INTEGER
);
```

```python
# File: scd_handler.py
class SCDType2Handler:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def update_lead_dimension(self, lead_id, new_data):
        """
        Handle SCD Type 2 update for lead dimension
        - Close current record (set valid_to, is_current=False)
        - Insert new record with new data
        """
        cursor = self.conn.cursor()

        # Close current record
        cursor.execute("""
            UPDATE dim_lead
            SET valid_to = CURRENT_DATE,
                is_current = FALSE
            WHERE lead_id = %s AND is_current = TRUE
        """, (lead_id,))

        # Insert new record
        cursor.execute("""
            INSERT INTO dim_lead (
                lead_id, company_name, industry, status,
                valid_from, is_current
            ) VALUES (%s, %s, %s, %s, CURRENT_DATE, TRUE)
        """, (
            lead_id,
            new_data['company_name'],
            new_data['industry'],
            new_data['status']
        ))

        self.conn.commit()
        cursor.close()

# Usage
scd = SCDType2Handler(db_config)
scd.update_lead_dimension(lead_id=123, new_data={
    'company_name': 'Acme Corp',
    'industry': 'Technology',
    'status': 'Qualified'
})
```

**Challenge:** Design and implement complete star schema for CRM

---

#### Session 6.2 (90 min) - ETL to Data Warehouse
**Concepts:** Dimension loading, fact loading, incremental updates
**Tasks:**
- Load dimension tables
- Load fact tables
- Implement incremental loads

**Exercise:**
```python
# File: warehouse_etl.py
from datetime import datetime, timedelta

class DataWarehouseETL:
    def __init__(self, source_db_config, warehouse_db_config):
        self.source_conn = psycopg2.connect(**source_db_config)
        self.warehouse_conn = psycopg2.connect(**warehouse_db_config)

    def load_date_dimension(self, start_date, end_date):
        """Populate date dimension for date range"""
        cursor = self.warehouse_conn.cursor()

        current_date = start_date
        while current_date <= end_date:
            date_key = int(current_date.strftime('%Y%m%d'))

            cursor.execute("""
                INSERT INTO dim_date (
                    date_key, date, year, quarter, month, month_name,
                    week, day_of_week, day_name, is_weekend, is_holiday
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (date_key) DO NOTHING
            """, (
                date_key,
                current_date,
                current_date.year,
                (current_date.month - 1) // 3 + 1,
                current_date.month,
                current_date.strftime('%B'),
                current_date.isocalendar()[1],
                current_date.weekday(),
                current_date.strftime('%A'),
                current_date.weekday() >= 5,
                False  # TODO: Check holiday calendar
            ))

            current_date += timedelta(days=1)

        self.warehouse_conn.commit()

    def load_lead_dimension(self):
        """Full load of lead dimension with SCD Type 2"""
        source_cursor = self.source_conn.cursor()
        warehouse_cursor = self.warehouse_conn.cursor()

        # Get all current leads from source
        source_cursor.execute("""
            SELECT id, company_name, industry, status, created_at
            FROM leads
        """)

        for row in source_cursor.fetchall():
            lead_id, company_name, industry, status, created_at = row

            # Check if lead already exists in dimension
            warehouse_cursor.execute("""
                SELECT lead_key, status
                FROM dim_lead
                WHERE lead_id = %s AND is_current = TRUE
            """, (lead_id,))

            existing = warehouse_cursor.fetchone()

            if existing:
                # Check if status changed (SCD Type 2)
                if existing[1] != status:
                    # Close current record
                    warehouse_cursor.execute("""
                        UPDATE dim_lead
                        SET valid_to = CURRENT_DATE, is_current = FALSE
                        WHERE lead_id = %s AND is_current = TRUE
                    """, (lead_id,))

                    # Insert new record
                    warehouse_cursor.execute("""
                        INSERT INTO dim_lead (
                            lead_id, company_name, industry, status,
                            valid_from, is_current
                        ) VALUES (%s, %s, %s, %s, CURRENT_DATE, TRUE)
                    """, (lead_id, company_name, industry, status))
            else:
                # New lead, insert
                warehouse_cursor.execute("""
                    INSERT INTO dim_lead (
                        lead_id, company_name, industry, status,
                        valid_from, is_current
                    ) VALUES (%s, %s, %s, %s, %s, TRUE)
                """, (lead_id, company_name, industry, status, created_at.date()))

        self.warehouse_conn.commit()

    def load_interaction_facts(self, load_date):
        """Incremental load of interaction facts for specific date"""
        source_cursor = self.source_conn.cursor()
        warehouse_cursor = self.warehouse_conn.cursor()

        date_key = int(load_date.strftime('%Y%m%d'))

        # Get interactions for the date
        source_cursor.execute("""
            SELECT
                i.id,
                i.lead_id,
                l.company_id,
                i.interaction_type,
                i.duration_minutes,
                i.outcome,
                i.interaction_date
            FROM interactions i
            JOIN leads l ON i.lead_id = l.id
            WHERE DATE(i.interaction_date) = %s
        """, (load_date,))

        for row in source_cursor.fetchall():
            (interaction_id, lead_id, company_id, interaction_type,
             duration, outcome, interaction_date) = row

            # Get dimension keys
            warehouse_cursor.execute("""
                SELECT lead_key FROM dim_lead
                WHERE lead_id = %s AND is_current = TRUE
            """, (lead_id,))
            lead_key = warehouse_cursor.fetchone()[0]

            warehouse_cursor.execute("""
                SELECT company_key FROM dim_company
                WHERE company_id = %s AND is_current = TRUE
            """, (company_id,))
            company_key = warehouse_cursor.fetchone()[0]

            # Insert fact
            warehouse_cursor.execute("""
                INSERT INTO fact_interactions (
                    date_key, lead_key, company_key,
                    interaction_type, duration_minutes, outcome,
                    meeting_scheduled, proposal_sent, converted
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                date_key, lead_key, company_key,
                interaction_type, duration, outcome,
                outcome == 'Meeting Scheduled',
                outcome == 'Proposal Sent',
                outcome == 'Converted'
            ))

        self.warehouse_conn.commit()

# Run ETL
etl = DataWarehouseETL(source_db_config, warehouse_db_config)

# Load dimensions (one-time)
etl.load_date_dimension(datetime(2025, 1, 1), datetime(2025, 12, 31))
etl.load_lead_dimension()

# Load facts (daily)
etl.load_interaction_facts(datetime.today())
```

**Challenge:** Build complete ETL loading all dimensions and facts

---

#### Session 6.3 (120 min) - Warehouse Analytics Queries
**Concepts:** OLAP queries, rollups, drill-downs
**Tasks:**
- Write analytics queries on star schema
- Create aggregate tables
- Build reports

**Exercise:**
```sql
-- File: warehouse_analytics.sql

-- Lead Conversion Funnel
SELECT
    dl.status,
    COUNT(DISTINCT dl.lead_key) as lead_count,
    ROUND(100.0 * COUNT(DISTINCT dl.lead_key) /
          SUM(COUNT(DISTINCT dl.lead_key)) OVER (), 2) as percentage
FROM dim_lead dl
WHERE dl.is_current = TRUE
GROUP BY dl.status
ORDER BY lead_count DESC;

-- Monthly Interaction Trends
SELECT
    dd.year,
    dd.month,
    dd.month_name,
    COUNT(*) as interaction_count,
    COUNT(DISTINCT fi.lead_key) as active_leads,
    AVG(fi.duration_minutes) as avg_duration
FROM fact_interactions fi
JOIN dim_date dd ON fi.date_key = dd.date_key
GROUP BY dd.year, dd.month, dd.month_name
ORDER BY dd.year, dd.month;

-- Industry Performance
SELECT
    dl.industry,
    COUNT(DISTINCT dl.lead_key) as total_leads,
    COUNT(DISTINCT CASE WHEN fi.converted THEN fi.lead_key END) as converted_leads,
    ROUND(100.0 * COUNT(DISTINCT CASE WHEN fi.converted THEN fi.lead_key END) /
          NULLIF(COUNT(DISTINCT dl.lead_key), 0), 2) as conversion_rate,
    SUM(fi.duration_minutes) as total_engagement_minutes
FROM dim_lead dl
LEFT JOIN fact_interactions fi ON dl.lead_key = fi.lead_key
WHERE dl.is_current = TRUE
GROUP BY dl.industry
ORDER BY conversion_rate DESC;

-- Lead Lifecycle Analysis
SELECT
    dl.lead_id,
    dl.company_name,
    MIN(dl.valid_from) as first_seen,
    MAX(CASE WHEN dl.is_current THEN NULL ELSE dl.valid_to END) as last_changed,
    COUNT(*) as status_changes,
    STRING_AGG(dl.status || ' (' || dl.valid_from || ')', ' Ã¢â€ â€™ ' ORDER BY dl.valid_from) as lifecycle
FROM dim_lead dl
GROUP BY dl.lead_id, dl.company_name
HAVING COUNT(*) > 1
ORDER BY status_changes DESC;

-- Daily Snapshot Report
SELECT
    dd.date,
    dl.status,
    COUNT(*) as lead_count,
    AVG(fds.days_in_status) as avg_days_in_status,
    AVG(fds.total_interactions) as avg_interactions
FROM fact_daily_leads fds
JOIN dim_date dd ON fds.date_key = dd.date_key
JOIN dim_lead dl ON fds.lead_key = dl.lead_key
WHERE dd.date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dd.date, dl.status
ORDER BY dd.date DESC, dl.status;
```

**Challenge:** Create 10 analytics queries for business insights

---

#### Session 6.4 (90 min) - Materialized Views & Aggregates
**Concepts:** Pre-aggregation, materialized views, incremental refresh
**Tasks:**
- Create materialized views
- Set up refresh schedules
- Optimize query performance

**Exercise:**
```sql
-- File: materialized_views.sql

-- Monthly summary (materialized view)
CREATE MATERIALIZED VIEW mv_monthly_summary AS
SELECT
    dd.year,
    dd.month,
    dl.industry,
    dl.status,
    COUNT(DISTINCT fi.lead_key) as active_leads,
    COUNT(*) as interaction_count,
    SUM(fi.duration_minutes) as total_duration,
    SUM(CASE WHEN fi.meeting_scheduled THEN 1 ELSE 0 END) as meetings_scheduled,
    SUM(CASE WHEN fi.converted THEN 1 ELSE 0 END) as conversions
FROM fact_interactions fi
JOIN dim_date dd ON fi.date_key = dd.date_key
JOIN dim_lead dl ON fi.lead_key = dl.lead_key
GROUP BY dd.year, dd.month, dl.industry, dl.status;

CREATE INDEX idx_mv_monthly_year_month ON mv_monthly_summary(year, month);

-- Refresh command (run daily)
REFRESH MATERIALIZED VIEW CONCURRENTLY mv_monthly_summary;

-- Lead engagement score (materialized view)
CREATE MATERIALIZED VIEW mv_lead_engagement AS
SELECT
    dl.lead_key,
    dl.lead_id,
    dl.company_name,
    dl.industry,
    dl.status,
    COUNT(fi.interaction_key) as total_interactions,
    SUM(fi.duration_minutes) as total_engagement_minutes,
    MAX(dd.date) as last_interaction_date,
    -- Engagement score calculation
    (COUNT(fi.interaction_key) * 10 +
     SUM(fi.duration_minutes) * 0.5 +
     SUM(CASE WHEN fi.meeting_scheduled THEN 50 ELSE 0 END)) as engagement_score
FROM dim_lead dl
LEFT JOIN fact_interactions fi ON dl.lead_key = fi.lead_key
LEFT JOIN dim_date dd ON fi.date_key = dd.date_key
WHERE dl.is_current = TRUE
GROUP BY dl.lead_key, dl.lead_id, dl.company_name, dl.industry, dl.status;

CREATE INDEX idx_mv_engagement_score ON mv_lead_engagement(engagement_score DESC);
```

```python
# File: materialized_view_refresh.py
class MaterializedViewManager:
    def __init__(self, db_config):
        self.conn = psycopg2.connect(**db_config)

    def refresh_view(self, view_name, concurrent=True):
        """Refresh materialized view"""
        cursor = self.conn.cursor()

        concurrent_clause = "CONCURRENTLY" if concurrent else ""
        sql = f"REFRESH MATERIALIZED VIEW {concurrent_clause} {view_name}"

        print(f"Refreshing {view_name}...")
        start = time.time()
        cursor.execute(sql)
        elapsed = time.time() - start

        self.conn.commit()
        print(f"Refreshed in {elapsed:.2f}s")

    def refresh_all_views(self):
        """Refresh all materialized views"""
        views = [
            'mv_monthly_summary',
            'mv_lead_engagement',
            'mv_industry_performance'
        ]

        for view in views:
            self.refresh_view(view)

# Schedule in Airflow
def refresh_materialized_views():
    manager = MaterializedViewManager(warehouse_db_config)
    manager.refresh_all_views()
```

**Challenge:** Create 3 materialized views for common queries

---

#### Session 6.5 (120 min) - Week 6 Mini-Project
**Project:** Production Data Warehouse
**Deliverables:**
1. Complete star schema with 4 dimensions, 2 fact tables
2. SCD Type 2 implementation for changing attributes
3. Full ETL pipeline loading all tables
4. 15 analytics queries for business reporting
5. 3 materialized views for performance
6. Airflow DAG orchestrating warehouse loads

**Integration Test:**
- Load 1M interactions into warehouse
- Verify SCD Type 2 working correctly
- Run all analytics queries (<1 second)
- Refresh materialized views
- Generate executive dashboard data

---

### Week 7-8: Production Readiness & Testing
**Goal:** Comprehensive testing, monitoring, deployment practices

#### Session 7.1 (120 min) - Unit Testing with pytest
**Concepts:** Test-driven development, fixtures, assertions, test organization
**Tasks:**
- Write comprehensive unit tests for all Python classes
- Use pytest fixtures for test setup/teardown
- Test edge cases and error conditions
- Achieve high test coverage

**Exercise:**
```python
# File: test_csv_loader.py
import pytest
from data_loader import CSVLoader

class TestCSVLoader:
    """Test suite for CSVLoader class"""

    @pytest.fixture
    def loader(self, db_config):
        loader = CSVLoader(db_config)
        yield loader
        loader.close()

    def test_load_valid_csv(self, loader, tmp_path):
        """Test loading valid CSV data"""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("company_name,email\nAcme,test@acme.com")

        loader.load_csv(str(csv_file), 'leads')
        count = loader.get_row_count('leads')
        assert count > 0

    def test_load_empty_csv(self, loader, tmp_path):
        """Test loading empty CSV raises appropriate error"""
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("company_name,email\n")

        # Should handle gracefully
        loader.load_csv(str(csv_file), 'leads')
        # Add assertions

    def test_invalid_connection(self):
        """Test invalid database connection raises error"""
        bad_config = {"host": "invalid", "database": "none"}
        with pytest.raises(Exception):
            CSVLoader(bad_config)
```

**Challenge:** Achieve 80%+ test coverage for all classes

---

#### Session 7.2 (90 min) - Integration Testing for Databases
**Concepts:** Test databases, transaction rollback, data fixtures
**Tasks:**
- Set up test database separate from development
- Use transactions for test isolation
- Create test data fixtures
- Test complete workflows

**Exercise:**
```python
# File: test_integration.py
import pytest
import psycopg2

@pytest.fixture(scope="session")
def test_db():
    """Create test database for integration tests"""
    # Create test database
    conn = psycopg2.connect(host="localhost", user="postgres", password="dev123")
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE IF EXISTS crm_test")
    cursor.execute("CREATE DATABASE crm_test")
    cursor.close()
    conn.close()

    yield {"host": "localhost", "database": "crm_test", "user": "postgres", "password": "dev123"}

    # Cleanup
    conn = psycopg2.connect(host="localhost", user="postgres", password="dev123")
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DROP DATABASE crm_test")

def test_complete_etl_workflow(test_db):
    """Test full ETL pipeline end-to-end"""
    # Setup: Create tables
    # Load: Insert test data
    # Transform: Run transformations
    # Verify: Check results
    pass
```

**Challenge:** Write 10 integration tests covering full workflows

---

#### Session 7.3 (120 min) - Test Fixtures & Mocking
**Concepts:** Pytest fixtures, mocking external dependencies, parametrized tests
**Tasks:**
- Create reusable test fixtures
- Mock external APIs and services
- Parametrize tests for multiple scenarios
- Test error handling

**Exercise:**
```python
# File: conftest.py (shared fixtures)
import pytest

@pytest.fixture
def sample_leads():
    """Fixture providing sample lead data"""
    return [
        {"company": "Acme", "email": "test@acme.com"},
        {"company": "Beta", "email": "test@beta.com"}
    ]

@pytest.fixture
def mock_api_response(monkeypatch):
    """Mock external API calls"""
    def mock_get(*args, **kwargs):
        return {"status": "success", "data": []}

    monkeypatch.setattr("requests.get", mock_get)

@pytest.mark.parametrize("status,expected", [
    ("New", 0),
    ("Qualified", 1),
    ("Converted", 2)
])
def test_status_mapping(status, expected):
    """Test status to integer mapping"""
    assert map_status(status) == expected
```

**Challenge:** Create fixture library for all test scenarios

---

#### Session 7.4 (90 min) - Data Quality Checks
**Concepts:** Data validation, assertions, quality metrics
**Tasks:**
- Implement data quality checks in pipeline
- Create validation rules
- Log and alert on quality issues
- Build quality dashboard

**Exercise:**
```python
# File: data_quality.py
class DataQualityChecker:
    """Validates data quality in ETL pipeline"""

    def check_completeness(self, df, required_columns):
        """Check no required columns are null"""
        for col in required_columns:
            null_count = df[col].isnull().sum()
            if null_count > 0:
                raise ValueError(f"{col} has {null_count} null values")

    def check_uniqueness(self, df, unique_columns):
        """Check specified columns are unique"""
        for col in unique_columns:
            if df[col].duplicated().any():
                raise ValueError(f"{col} has duplicate values")

    def check_range(self, df, column, min_val, max_val):
        """Check values are within expected range"""
        out_of_range = df[(df[column] < min_val) | (df[column] > max_val)]
        if len(out_of_range) > 0:
            raise ValueError(f"{len(out_of_range)} values outside range")
```

**Challenge:** Build complete quality check suite for CRM data

---

#### Session 7.5 (120 min) - CI/CD & Test Automation
**Concepts:** GitHub Actions, automated testing, deployment pipelines
**Tasks:**
- Set up GitHub Actions workflow
- Automate test execution
- Add linting and code quality checks
- Create deployment pipeline

**Exercise:**
```yaml
# File: .github/workflows/test.yml
name: Test Suite

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: dev123
          POSTGRES_DB: crm_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v2

      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov

      - name: Run tests
        run: |
          pytest --cov=. --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v2
```

**Challenge:** Set up complete CI/CD pipeline with automated deployments

---

### Week 7-8 Mini-Project
**Project:** Production-Ready Tested System
**Deliverables:**
1. Unit test suite (80%+ coverage)
2. Integration test suite (all workflows)
3. Data quality checks integrated in pipeline
4. CI/CD pipeline with automated testing
5. Monitoring and alerting setup
6. Complete documentation

**Integration Test:**
- All unit tests pass
- All integration tests pass
- CI/CD pipeline runs successfully
- Data quality checks catch intentional errors
- System deployable with one command

---

## PHASE 3: PRODUCTION DEPLOYMENT (Weeks 9-12)
### Build: Cloud Deployment & Final Project

[Continue with final 4 weeks covering: cloud deployment (AWS/GCP), infrastructure as code, security, final capstone project]

---

## Daily Session Structure (Standard Template)

Each 90-120 minute session follows this structure:

1. **Review (10 min)**
   - Quick recap of previous session
   - Answer questions
   - Connect to today's topic

2. **Concept Introduction (15-20 min)**
   - Explain new concept
   - Why it matters
   - Real-world examples

3. **Hands-On Exercise (40-60 min)**
   - Code along with examples
   - Build incrementally
   - Test and debug

4. **Challenge Problem (20-30 min)**
   - Apply what you learned
   - Work independently
   - More complex scenario

5. **Wrap-Up (5-10 min)**
   - Review what you built
   - Preview next session
   - Assign mini-homework

---

## Progress Tracking

Mark each session as you complete it:
- [ ] Session X.Y - Topic Name

Complete week when all 5 sessions done:
- [ ] Week X Mini-Project

Complete phase when all weeks done:
- [ ] Phase X Final Project

---

## Success Criteria

**After Phase 1 (Week 4):**
- [ ] Can build end-to-end ETL pipeline
- [ ] Comfortable with Python OOP
- [ ] Write complex SQL queries
- [ ] Create Airflow DAGs

**After Phase 2 (Week 8):**
- [ ] Process data with Spark at scale
- [ ] Design and build data warehouse
- [ ] Optimize for performance
- [ ] Implement production patterns

**After Phase 3 (Week 12):**
- [ ] Deploy to cloud (AWS/GCP)
- [ ] Monitor production pipelines
- [ ] Handle errors gracefully
- [ ] Document everything

**Final Test:**
Build a complete data platform from scratch in 2 days.
