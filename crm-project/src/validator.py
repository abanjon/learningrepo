import re
from datetime import datetime

class ValidationError(Exception):
    """Custom exception for validation failure"""
    pass

class LeadValidator:
    """
    Validated lead data before database insertion.

    Design pattern: Collect all errors instead of fail-fast.
    This gives user complete feedback, not just first error.
    """

    def __init__(self):
        """Initialize with empty error list"""
        self.errors = [] # List to collect all validation errors

    def validate_lead(self, lead):
        """
        Validate a single lead record

        Args:
            lead: Dictionary with lead data

        Returns:
            bool: True if valid, False if errors found

        Side effect: Populates self.errors list
        """
        # Clear previous errors
        self.errors = []

        # Run all validation checks
        # Note: We DON'T use try-except here because we want
        # to collect all errors, not stop at first one
        self._validate_company_name(lead)
        self._validate_email(lead)
        self._validate_industry(lead)
        self._validate_status(lead)
        self._validate_phone(lead)
        self._validate_website(lead)
        self._validate_cross_field(lead)

        # Return True if no errors found
        return len(self.errors) == 0

    def _validate_company_name(self, lead):
        """
        Validate company name field.

        Rules:
        - Required (not None, not empty)
        - Between 2 and 255 characters
        - No special characters except spaces, hyphens, ampersands

        Why underscore prefix (_validate)?
        Indicates tis is private - only used internally
        """
        company = lead.get("company_name")

        # Check if exists
        if not company:
            self.errors.append("Company name is required")
            return

        # Check length
        if len(company) < 2:
            self.errors.append("Company name must be at least 2 characters")

        if len(company) > 255:
            self.errors.append("Company name cannot exceed 255 characters")

        # Check for invalid characters
        # Regex ^ = start, $ = end, [] = allowed chars, + = one or more
        if not re.match(r'^[a-zA-Z0-9\s\-&.]+$', company):
            self.errors.append("Company name contains invalid characters")

    def _validate_email(self, lead):
        """
        Validate email field.

        Rules:
        - Required
        - Valid email format (simple check)
        - Max 255 chars
        """
        email = lead.get("email")

        if not email:
            self.errors.append("Email is required")
            return

        # Simple email regex
        # Breakdown: something @ something . something
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            self.errors.append("Invalid email format")

        if len(email) > 255:
            self.errors.append("Email cannot exceed 255 chars")

    def _validate_industry(self, lead):
        """
        Validate industry field

        Rules:
        - Optional (can be None or empty)
        - If provided, must be from allowed list
        """
        industry = lead.get("industry")

        # Allowed industries (business logic)
        allowed_industries = [
            "Technology",
            "Healthcare",
            "Finance",
            "Manufacturing",
            "Retail",
            "Education",
            "Other"
        ]

        # Skip validation if not provided (optional field)
        if not industry:
            return

        if industry not in allowed_industries:
            self.errors.append(
                f"Industry must be of of: {', '.join(allowed_industries)}"
            )

    def _validate_status(self, lead):
        """
        Validate status field.

        Rules:
        - Optional (defaults no 'New' in database)
        - If provided, must be valid status
        """
        status = lead.get("status")

        valid_statuses = ["New", "Contacted", "Qualified", "Proposal Sent", "Converted", "Lost"]

        if not status:
            return

        if status not in valid_statuses:
            self.errors.append(
                f"Status must be one of: {', '.join(valid_statuses)}"
            )

    def _validate_phone(self, lead):
        phone_num = lead.get("phone_num")

        if not phone_num:
            return

        phone_num_pattern = r'^\(?\d{3}\)?[-\s]?\d{3}[-\s]?\d{4}$'
        if not re.match(phone_num_pattern, phone_num):
            self.errors.append("Invalid phone number")

    def _validate_website(self, lead):
        website = lead.get("website")

        if not website:
            return

        if not (website.startswith("http://") or website.startswith("https://")):
            self.errors.append("Website must start with http:// or https://")
            return

        if "." not in website:
            self.errors.append("Website must contain a domain")

    def _validate_cross_field(self, lead):
        status = lead.get("status")
        contact_person = lead.get("contact_person")

        if (status == "Converted" and contact_person == ""):
            self.errors.append("Status cannot be converted without contact person")



    def get_errors(self):
        """Return list of all validation errors"""
        return self.errors

    def is_valid(self):
        """Check if last validation passed"""
        return len(self.errors) == 0
