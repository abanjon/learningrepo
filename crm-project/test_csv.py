# test_csv.py
import config
from src.data_loader import CSVLoader

# Test 1: Test context manager works
print("Test 1: Testing CSVLoader context manager")
db_config = config.DB_CONFIG

with CSVLoader(db_config) as loader:
    print("✓ Context manager works!")

    # Test 2: Try to load a file
    print("\nTest 2: Testing load_csv")
    try:
        stats = loader.load_csv("data/input/sales_team_east.csv", "leads")
        print(f"✓ Load successful: {stats}")
    except Exception as e:
        print(f"✗ Load failed: {e}")
        import traceback

        traceback.print_exc()

print("\nTest complete!")
