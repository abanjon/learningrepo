import os
import csv
import random
import config

from faker import Faker


fake = Faker()


def ensure_dirs():
    """Make sure input directory exists"""
    os.makedirs("data/input", exist_ok=True)


def generate_valid_lead():
    """Generate one valid lead for testing"""
    return {
        "company_name": fake.company(),
        "contact_person": fake.name(),
        "email": fake.email(),
        "industry": random.choice(config.ALLOWED_INDUSTRIES),
        "status": random.choice(config.VALID_STATUSES),
    }


def generate_invalid_lead():
    """Generate one invalid lead for testing"""
    return {
        "company_name": "",
        "contact_person": fake.name(),
        "email": "lol_no_email.com",
        "industry": "Olympic Curling",
        "status": "Trolling",
    }


def generate_missing_req_field():
    """Generate lead with missing required field"""
    lead = generate_valid_lead()

    if random.random() < 0.5:
        lead["company_name"] = ""
    else:
        lead["email"] = ""
    return lead


def generate_invalid_format():
    """Generate lead with invalid email format"""
    lead = generate_valid_lead()
    lead["email"] = "lolnotemail.com"
    return lead


def generate_duplicate_email(existing_emails):
    """Generate lead with email that already exists"""
    lead = generate_valid_lead()

    if existing_emails:
        lead["email"] = random.choice(existing_emails)
    return lead


def generate_invalid_industry():
    """Generate lead with industry not in ALLOWED_INDUSTRIES"""
    lead = generate_valid_lead()
    lead["industry"] = "Olympic Curling"
    return lead


def generate_cross_field_error():
    """Generate lead with status='Converted' but no contact person"""
    lead = generate_valid_lead()
    lead["status"] = "Converted"
    lead["contact_person"] = ""
    return lead


def write_csv(filename, data):
    with open(filename, "w", newline="") as f:
        fieldnames = ["company_name", "contact_person", "email", "industry", "status"]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def generate_sales_team_east():
    """Generate sales_team_east.csv (50 rows)"""
    print("Generating sales_team_east.csv...")

    leads = []
    email_tracker = []  # Keep track of emails for potential duplicates later

    # 40 valid rows (80%)
    for _ in range(40):
        lead = generate_valid_lead()
        email_tracker.append(lead["email"])
        leads.append(lead)

    # 5 missing required fields (10%)
    for _ in range(5):
        leads.append(generate_missing_req_field())

    # 5 invalid emails (10%)
    for _ in range(5):
        leads.append(generate_invalid_format())

    # Shuffle and write
    random.shuffle(leads)
    write_csv("data/input/sales_team_east.csv", leads)
    print("  Created with: 40 valid, 5 missing fields, 5 invalid emails")
    return email_tracker


def generate_sales_team_west(existing_emails):
    """Generate sales_team_west.csv (50 rows)"""
    print("Generating sales_team_west.csv...")

    leads = []
    all_emails = existing_emails.copy()

    # 35 valid rows (70%)
    for _ in range(35):
        lead = generate_valid_lead()
        all_emails.append(lead["email"])
        leads.append(lead)

    # 10 duplicate emails (20%) - use emails from east team
    for _ in range(10):
        leads.append(generate_duplicate_email(existing_emails))

    # 5 invalid industry (10%)
    for _ in range(5):
        leads.append(generate_invalid_industry())

    # Shuffle and write
    random.shuffle(leads)
    write_csv("data/input/sales_team_west.csv", leads)
    print("  Created with: 35 valid, 10 duplicate emails, 5 invalid industry")
    return all_emails


def generate_sales_team_south():
    """Generate sales_team_south.csv (50 rows)"""
    print("Generating sales_team_south.csv...")

    leads = []

    # 45 valid rows (90%)
    for _ in range(45):
        leads.append(generate_valid_lead())

    # 5 cross-field validation errors (10%)
    for _ in range(5):
        leads.append(generate_cross_field_error())

    # Shuffle and write
    random.shuffle(leads)
    write_csv("data/input/sales_team_south.csv", leads)
    print("  Created with: 45 valid, 5 cross-field errors")


def generate_invalid_leads():
    print("Generating invalid_leads.csv")

    leads = []

    for _ in range(20):
        leads.append(generate_invalid_industry())

    for _ in range(30):
        leads.append(generate_missing_req_field())

    random.shuffle(leads)
    write_csv("data/input/invalid_leads.csv", leads)
    print("  Created with 50 invalid leads.")


def main():
    """Generate all 3 test files"""
    print("=" * 50)
    print("Generating ETL Test Data Files")
    print("=" * 50)

    ensure_dirs()

    # Generate files in sequence, passing emails for duplicates
    east_emails = generate_sales_team_east()
    print()

    generate_sales_team_west(east_emails)
    print()

    generate_sales_team_south()
    print()

    generate_invalid_leads()
    print()

    print("=" * 50)
    print("All files generated in data/input/ directory:")
    print("  • sales_team_east.csv  (50 rows)")
    print("  • sales_team_west.csv  (50 rows)")
    print("  • sales_team_south.csv (50 rows)")
    print("=" * 50)


if __name__ == "__main__":
    main()
