# main.py
from validator import OrderValidator

SAMPLE_ORDERS = [
    {
        "customer_email": "alice@example.com",
        "total_amount": 99.99,
        "order_date": "2024-03-01",
    },
    {
        "customer_email": "bad-email",
        "total_amount": -10.00,
        "order_date": "2024-03-02",
    },  # 2 errors
    {
        "customer_email": "bob@example.com",
        "total_amount": "not-a-number",
        "order_date": "2024-03-03",
    },  # 1 error
    {
        "customer_email": "charlie@example.com",
        "total_amount": 50.00,
        "order_date": "2024-03-04",
    },
]


def main():
    validator = OrderValidator()
    validator.process_batch(SAMPLE_ORDERS)

    print("\n--- Processing Results ---")
    print(f"Valid Orders: {len(validator.valid_orders)}")
    print(f"Invalid Records: {len(validator.errors_by_record)}")

    if validator.errors_by_record:
        print("\nDetailed Errors:")
        for idx, errors in validator.errors_by_record.items():
            print(f"  Record {idx}:")
            for e in errors:
                print(f"    - {e}")


if __name__ == "__main__":
    main()
