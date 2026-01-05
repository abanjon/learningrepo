# File: validation_report.py
"""
Analyzes error log and generates CSV report with statistics.
"""
import csv
import re
from collections import Counter
from datetime import datetime

def parse_error_log(log_file='etl_errors.log'):
    """
    Parse error log file and extract structured data.

    Returns:
        list of dicts: [{
            'timestamp': '2025-12-11 10:30:00',
            'row_number': 5,
            'error_type': 'validation',
            'error_message': 'Email is required',
            'data': {...}
        }, ...]
    """
    errors = []

    with open(log_file, 'r') as f:
        lines = f.readlines()

    current_error = None

    for line in lines:
        line = line.strip()

        # Check if this is an error line
        if 'ERROR' in line and 'Row' in line:
            # Extract row number
            match = re.search(r'Row (\d+):', line)
            if match:
                row_num = int(match.group(1))

                # Extract error type
                if 'Validation failed' in line:
                    error_type = 'validation'
                elif 'Database error' in line:
                    error_type = 'database'
                else:
                    error_type = 'unknown'

                # Extract timestamp (first part before ' - ')
                timestamp = line.split(' - ')[0]

                current_error = {
                    'timestamp': timestamp,
                    'row_number': row_num,
                    'error_type': error_type,
                    'error_messages': [],
                    'data': None
                }

        # Collect error messages
        elif current_error and 'Errors:' in line:
            # Extract the errors list
            errors_str = line.split('Errors:')[1].strip()
            current_error['error_messages'] = eval(errors_str)  # Parse list

        # Collect data
        elif current_error and 'Data:' in line:
            data_str = line.split('Data:')[1].strip()
            try:
                current_error['data'] = eval(data_str)  # Parse dict
            except:
                current_error['data'] = data_str

            # Error is complete, add to list
            errors.append(current_error)
            current_error = None

    return errors

def generate_error_summary(errors):
    """
    Generate summary statistics from errors.

    Returns:
        dict with statistics
    """
    # Count by error type
    error_types = Counter([e['error_type'] for e in errors])

    # Count specific validation errors
    validation_errors = []
    for error in errors:
        if error['error_type'] == 'validation':
            validation_errors.extend(error['error_messages'])

    validation_error_counts = Counter(validation_errors)

    return {
        'total_errors': len(errors),
        'by_type': dict(error_types),
        'validation_error_details': dict(validation_error_counts)
    }

def export_error_report(errors, output_file='error_report.csv'):
    """Export errors to CSV for review"""

    if not errors:
        print("No errors to report")
        return

    with open(output_file, 'w', newline='') as f:
        fieldnames = ['timestamp', 'row_number', 'error_type', 'error_messages', 'company_name', 'email']
        writer = csv.DictWriter(f, fieldnames=fieldnames)

        writer.writeheader()

        for error in errors:
            writer.writerow({
                'timestamp': error['timestamp'],
                'row_number': error['row_number'],
                'error_type': error['error_type'],
                'error_messages': '; '.join(error['error_messages']) if isinstance(error['error_messages'], list) else str(error['error_messages']),
                'company_name': error['data'].get('company_name', '') if error['data'] else '',
                'email': error['data'].get('email', '') if error['data'] else ''
            })

    print(f"Error report exported to {output_file}")

def main():
    """Generate validation report"""
    print("Parsing error log...")
    errors = parse_error_log('etl_errors.log')

    print(f"Found {len(errors)} errors")

    # Generate summary
    summary = generate_error_summary(errors)

    print("\n" + "=" * 60)
    print("ERROR SUMMARY")
    print("=" * 60)
    print(f"Total errors: {summary['total_errors']}")
    print(f"\nBy type:")
    for error_type, count in summary['by_type'].items():
        print(f"  {error_type}: {count}")

    print(f"\nValidation error details:")
    for error, count in summary['validation_error_details'].items():
        print(f"  {error}: {count}")

    # Export to CSV
    export_error_report(errors)

    print("\n" + "=" * 60)
    print("Report generation complete!")
    print("  - error_report.csv (detailed errors)")
    print("  - Summary printed above")

if __name__ == "__main__":
    main()
