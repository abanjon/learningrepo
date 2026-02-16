# persistence.py
import json
import logging

from db import get_connection
from main import SAMPLE_ORDERS
from validator import OrderValidator

logger = logging.getLogger(__name__)


class OrderPersistence:
    """Saves valid orders to db and logs invalid records to JSON"""

    def __init__(self, validation):
        self.validation = validation

    def save_to_db(self):
        conn = None
        cursor = None
        try:
            conn = get_connection()
            cursor = conn.cursor()

            row_count = 0

            for valid_order in self.validation.valid_orders:
                cursor.execute(
                    """insert into orders (customer_email, order_date, total_amount, status) values (%s, %s, %s, %s)""",
                    (
                        valid_order["customer_email"],
                        valid_order["order_date"],
                        valid_order["total_amount"],
                        valid_order["status"],
                    ),
                )
                row_count += cursor.rowcount

            logger.info(f"{row_count} successfully inserted!")
            conn.commit()

        except Exception as e:
            logger.error("Database error occured: %s", e)
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()

    def save_errors_to_json(self, filepath):
        validation_errors = []

        for record_idx, error_list in self.validation.errors_by_record.items():
            for e in error_list:
                validation_errors.append(f"Record {record_idx}: {e}")

        with open(filepath, "w") as error_json:
            json.dump(validation_errors, error_json)


if __name__ == "__main__":
    validator = OrderValidator()
    validator.process_batch(SAMPLE_ORDERS)
    persistor = OrderPersistence(validator)
    persistor.save_to_db()
    persistor.save_errors_to_json("failed_orders.json")
