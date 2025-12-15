# File: test_queries.py
import psycopg2
from query_runner import QueryRunner

# Database config
db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
}

# Create QueryRunner instance
runner = QueryRunner(db_config)

# Test 1: Run query and print results
print("=" * 80)
print("TEST 1: Lead distribution by status")
print("=" * 80)
results = runner.run_query("""
    SELECT
        status,
        COUNT(*) as lead_count,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM leads), 2) as percentage
    FROM leads
    GROUP BY status
    ORDER BY lead_count DESC
""")

for row in results:
    print(f"{row['status']:20} {row['lead_count']:5} leads ({row['percentage']:5.2f}%)")

# Test 2: Export to CSV
print("\n" + "=" * 80)
print("TEST 2: Export all leads to CSV")
print("=" * 80)
count = runner.export_to_csv(
    "SELECT * FROM leads ORDER BY created_at DESC",
    "all_leads_export.csv"
)
print(f"Check all_leads_export.csv - should have {count} rows")

# Test 3: Parametrized query
print("\n" + "=" * 80)
print("TEST 3: Filter by status (parametrized)")
print("=" * 80)
new_leads = runner.run_query(
    "SELECT company_name, email FROM leads WHERE status = %s",
    ("New",)  # Note the comma - makes it a tuple
)
print(f"Found {len(new_leads)} new leads:")
for lead in new_leads[:5]:  # Show first 5
    print(f"  - {lead['company_name']} ({lead['email']})")

# Test 4: Table summary stats
print("\n" + "=" * 80)
print("TEST 4: Table summary")
print("=" * 80)
stats = runner.get_summary_stats('leads')
print(f"Total rows: {stats['total_rows']}")
print("Columns:")
for col in stats['columns']:
    print(f"  - {col['column_name']:20} ({col['data_type']})")

# Close connection
runner.close()
