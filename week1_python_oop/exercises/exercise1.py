class Lead:
    def __init__(self, company_name, contact_person, email, status):
        self.company_name = company_name
        self.contact_person = contact_person
        self.email = email
        self.status = status # "New", "Contacted", "Qualified", "Lost" 
        
        
    def update_status(self, new_status):
        self.status = new_status
        
    
    def display_info(self):
        print(f"Company: {self.company_name}")
        print(f"Email: {self.email}")
        print(f"Contact Person: {self.contact_person}")
        print(f"Status: {self.status}")


    
class LeadManager:
    def __init__(self):
        self.leads = []  # List to store all leads
        
    def add_lead(self, lead):
        self.leads.append(lead)
    
    def get_lead_by_company(self, company_name):
        # Find and return a lead by company name
        # Return None if not found
        print(f"Searching for: {company_name}")
        print(f"Nunber of leads to search: {len(self.leads)}")
        for lead in self.leads:
            if company_name == lead.company_name:
                return lead
            
        return None            
    
    def get_leads_by_status(self, status):
        # Return a list of all leads with given status
        matching_leads = []
        for lead in self.leads:
            if lead.status == status:
                matching_leads.append(lead)
        return matching_leads
        
    def display_all_leads(self):
        for lead in self.leads:
            print(f"Company: {lead.company_name}")
            print(f"Email: {lead.email}")
            print(f"Contact Person: {lead.contact_person}")
            print(f"Status: {lead.status}")    
        

# Test it:
manager = LeadManager()

lead1 = Lead("Google", "Sundar Pichai", "sundar@google.com", "New")
lead2 = Lead("Amazon", "Andy Jassy", "andy@amazon.com", "Contacted")
lead3 = Lead("Apple", "Tim Cook", "tim@apple.com", "New")

manager.add_lead(lead1)
manager.add_lead(lead2)
manager.add_lead(lead3)

# Find Google
google_lead = manager.get_lead_by_company("Google")

google_lead.display_info()

# Get all "New" leads
new_leads = manager.get_leads_by_status("New")
print(f"\nFound {len(new_leads)} new leads")

# Display all
manager.display_all_leads()