# 1. Given this list, create a dict counting occurrences
statuses = ["New", "Qualified", "New", "Converted", "New"]
# Expected: {"New": 3, "Qualified": 1, "Converted": 1}

status_count = {}
counted = []

for status in statuses:
    if status in counted:
        pass
    else:
        status_count[status] = statuses.count(status)
        counted.append(status)

#print(status_count)


"""
status_count = {}
for status in statuses:
    status_count[status] = status_count.get(status, 0) + 1

# Or even simpler with Counter:
from collections import Counter
status_count = Counter(statuses)
"""

# 2. Filter to only emails from ".com" domains
emails = ["test@acme.com", "bob@nonprofit.org", "alice@startup.com", "test@usa.gov", "jeff@google.org"]
# Expected: ["test@acme.com", "alice@startup.com"]


#INCORRECT
for email in emails:
    if email.endswith('.com'):
        pass
    else:
        emails.remove(email)

#print(emails)

"""
com_emails = [email for email in emails if email.endswith('.com')]

com_emails = list(filter(lambda email: email.endswith('.com'), emails))

for email in emails[:]:  # [:] creates a copy
    if not email.endswith('.com'):
        emails.remove(email)
"""

# 3. Group these by industry
leads = [
    {"company": "A", "industry": "Tech"},
    {"company": "B", "industry": "Finance"},
    {"company": "C", "industry": "Tech"}
]
# Expected: {"Tech": [...], "Finance": [...]}

from collections import defaultdict

grouped = defaultdict(list)

for lead in leads:
    grouped[lead["industry"]].append(lead)

#print(dict(grouped))

# 4. Convert this list of tuples to list of dicts
columns = ["id", "name", "email"]
rows = [(1, "Acme", "a@test.com"), (2, "Beta", "b@test.com")]
# Expected: [{"id": 1, "name": "Acme", ...}, {...}]

"""
result = []
for row in rows:
    row_dict = dict(zip(columns, row))
    result.append(row_dict)

print(result)
"""

# 5. Get unique industries from leads
leads = [
    {"industry": "Tech"},
    {"industry": "Finance"},
    {"industry": "Tech"}
]
# Expected: ["Tech", "Finance"]

#INCORRECT
unique_industries= [lead["industry"] for lead in leads if lead["industry"] not in leads]

#print(unique_industries)


"""
seen = set()
unique_industries = []

for lead in leads:
    industry = lead["industry"]
    if industry not in seen:
        unique_industries.append(industry)
        seen.add(industry)

print(unique_industries)  # ["Tech", "Finance"]

# Extract all industries, let set() remove duplicates
unique_industries = list(set([lead["industry"] for lead in leads]))
print(unique_industries)  # ["Tech", "Finance"] (order may vary)

unique_industries = list(dict.fromkeys([lead["industry"] for lead in leads]))
print(unique_industries)  # ["Tech", "Finance"] (order preserved)
 """
