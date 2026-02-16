# main.py
from validator import InspectionValidator

SAMPLE_RECORDS = [
    {
        "restaurant_name": "Joe's Diner",
        "inspection_date": "2024-03-15",
        "score": 92,
        "violations": "Minor: food storage temperature",
        "inspector_id": "INS-1234",
    },
    {
        "restaurant_name": "Pizza Palace",
        "inspection_date": "2024-03-16",
        "score": 78,
        "violations": "Major: pest evidence; Minor: handwashing",
        "inspector_id": "INS-5678",
    },
    {
        # Record 3: FOUR errors (empty name, bad date, bad score, bad ID)
        "restaurant_name": "",
        "inspection_date": "not-a-date",
        "score": 150,
        "violations": "",
        "inspector_id": "BADGE-99",
    },
    {
        "restaurant_name": "Taco Town",
        "inspection_date": "2024-03-17",
        "score": 85,
        "violations": "",
        "inspector_id": "INS-9012",
    },
    {
        "restaurant_name": "Burger Barn",
        "inspection_date": "03/18/2024",  # Wrong format
        "score": 65,
        "violations": "Critical: cross-contamination",
        "inspector_id": "INS-3456",
    },
    {
        "restaurant_name": "Sushi Spot",
        "inspection_date": "2024-03-19",
        "score": "ninety",  # Not an integer
        "violations": "Minor: labeling",
        "inspector_id": "INS-7890",
    },
    {
        "restaurant_name": "Green Leaf Cafe",
        "inspection_date": "2024-03-20",
        "score": 95,
        "violations": "",
        "inspector_id": "INS-2345",
    },
    {
        "restaurant_name": "  ",  # Whitespace only
        "inspection_date": "2024-03-20",
        "score": 88,
        "violations": "",
        "inspector_id": "INS-6789",
    },
]


def main():
    validator = InspectionValidator()
    valid_records = validator.validate_batch(SAMPLE_RECORDS)

    print(f"\n{'=' * 50}")
    print("  Validation Results")
    print(f"{'=' * 50}")

    summary = validator.get_summary()
    for key, value in summary.items():
        print(f"  {key}: {value}")

    if validator.invalid_records:
        print("\n  Failed Records:")
        for error in validator.invalid_records:
            print(f"    Record {error.record_num}:")
            for field_error in error.errors:
                print(f"      - {field_error}")

    print("\n  Valid records ready for insertion:")
    for record in valid_records:
        print(f"    {record['restaurant_name']} (score: {record['score']})")


if __name__ == "__main__":
    main()
