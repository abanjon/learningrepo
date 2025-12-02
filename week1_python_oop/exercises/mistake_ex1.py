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
        new_lead = self.leads.copy()
        new_lead.append(lead)
        return new_lead
    
    def get_lead_by_company(self, company_name):
        # Find and return a lead by company name
        # Return None if not found
        for lead in self.leads:
            if company_name == self.company_name:
                return self.leads
            else:
                return None            
    
    def get_leads_by_status(self, status):
        # Return a list of all leads with given status
        for lead in self.leads:
            if status == self.status:
                return self.leads
        
    def display_all_leads(self):
        for lead in self.leads:
            print(f"Company: {self.company_name}")
            print(f"Email: {self.email}")
            print(f"Contact Person: {self.contact_person}")
            print(f"Status: {self.status}")    
        
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