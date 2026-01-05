from data_loader import CSVLoader
import csv

# Create test CSV with mixed valid/invalid data
test_data = [
    # Valid
    {"company_name": "Acme Corp", "contact_person": "John", "email": "john@acme.com", "industry": "Technology", "status": "New"},

    # Invalid - missing company
    {"company_name": "", "contact_person": "Jane", "email": "jane@test.com", "industry": "Finance", "status": "New"},

    # Invalid - bad email
    {"company_name": "Beta Inc", "contact_person": "Bob", "email": "not-an-email", "industry": "Healthcare", "status": "New"},

    # Invalid - bad industry
    {"company_name": "Gamma LLC", "contact_person": "Alice", "email": "alice@gamma.com", "industry": "InvalidIndustry", "status": "New"},

    # Valid
    {"company_name": "Delta Co", "contact_person": "Charlie", "email": "charlie@delta.com", "industry": "Manufacturing", "status": "Qualified"},

    # Row 6 - should be valid
    {"company_name": "AMC", "contact_person": "Charlie", "email": "charlie@amc.com",
    "phone_num": "(240)4808282", "website": "https://google.com"},  # ← Fixed

    # Row 7 - invalid phone (too many digits)
    {"company_name": "Apple", "contact_person": "Steve", "email": "steve@apple.com",
    "phone_num": "(240)34808282", "website": "https://apple.com"},  # ← Fixed

    # Row 8 - invalid website (no http)
    {"company_name": "Meta", "contact_person": "Mark", "email": "mark@meta.com",
    "phone_num": "(240)4808282", "website": "google.com"},  # ← This should fail

    # Row 9 - invalid cross-field
    {"company_name": "Netflix", "contact_person": "", "email": "info@netflix.com",
    "status": "Converted", "phone_num": "(240)4808282", "website": "https://netflix.com"},
]

# Write test CSV
with open('test_validation.csv', 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=["company_name", "contact_person", "email", "industry", "status", "phone_num", "website", "contact_person"])
    writer.writeheader()
    writer.writerows(test_data)

db_config = {
    "host": "localhost",
    "database": "crm_dev",
    "user": "postgres",
    "password": "dev123"
}

loader = CSVLoader(db_config)
loader.clear_table('leads')

stats = loader.load_csv('test_validation.csv', 'leads')

if stats['failed'] > 0:
    print("\n" + "=" * 80)
    print("VALIDATION ERRORS:")
    print("=" * 80)
    for error in stats['errors']:
        print(f"\nRow {error['row']}: {error['data']['company_name']}")
        print(f"  Errors: {error['error']}")

loader.close()
