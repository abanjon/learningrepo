# validation_report.py

from main import SAMPLE_RECORDS
from validator import InspectionValidator


class ValidationReport:
    def __init__(self, validation):
        self.validation = validation

    def generate(self):
        report_lines = []

        summary = self.validation.get_summary()

        report_lines.append(f"Summary: {summary}")

        field_counts = {}
        for invalid_record in self.validation.invalid_records:
            for error in invalid_record.errors:
                if error.field in field_counts:
                    field_counts[error.field] += 1
                else:
                    field_counts[error.field] = 1

        if field_counts:
            report_lines.append(f"Errors per field: {field_counts}")

            highest_field = max(field_counts.items(), key=lambda item: item[1])
            field_name = highest_field[0]

            report_lines.append(f"Most common error field: {field_name}")

            sum_errors = sum(field_counts.values())
            report_lines.append(f"Total errors: {sum_errors}")

        # * The restaurant with the lowest inspection score.
        # * The restaurant with the highest inspection score.
        # * The average score across all valid records.

        if self.validation.valid_records:
            highest_score_record = max(
                self.validation.valid_records, key=lambda r: r["score"]
            )
            report_lines.append(
                f"Highest inspection score: {highest_score_record.get('restaurant_name')}"
            )

            lowest_score_record = min(
                self.validation.valid_records, key=lambda r: r["score"]
            )
            report_lines.append(
                f"Lowest inspection score: {lowest_score_record.get('restaurant_name')}"
            )

            scores = [r["score"] for r in self.validation.valid_records]
            avg_score = sum(scores) / len(scores)
            report_lines.append(f"Average inspection score: {avg_score}")

        return "\n".join(report_lines)

    def save_to_file(self, filepath: str):
        report_content = self.generate()
        with open(filepath, "w") as f:
            f.write(report_content)


if __name__ == "__main__":
    validator = InspectionValidator()
    validator.validate_batch(SAMPLE_RECORDS)

    report = ValidationReport(validator)
    report.generate()
    report.save_to_file("report.txt")
