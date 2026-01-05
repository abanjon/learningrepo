-- Unique email (prevent duplicates)
ALTER TABLE leads
ADD CONSTRAINT unqique_email UNIQUE (email);

-- Status must be valid
ALTER TABLE leads
ADD CONSTRAINT check_status
CHECK (status IN ('New', 'Contacted', 'Qualified', 'Proposal Sent', 'Converted', 'Lost'));

-- Email must contain @
ALTER TABLE leads
ADD constraint check_email_format
CHECK (email LIKE '%@%');

-- Company name cannot be empty
ALTER TABLE leads
ADD CONSTRAINT check_company_not_empty
CHECK (LENGTH(TRIM(company_name)) > 0);

ALTER TABLE leads ADD COLUMN phone VARCHAR(20);
ALTER TABLE leads ADD COLUMN website VARCHAR(255);
