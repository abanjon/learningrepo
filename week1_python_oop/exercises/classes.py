""" class Lead:
    pass


# Create an instance
lead1 = Lead()
print(lead1) """

# Returns: ❯ /bin/python3 /home/aban/data_engineering_learning/week1_python_oop/exercises/classes.py <__main__.Lead object at 0x7ebe87726c80>

""" class Lead:
    def __init__(self, company_name, email):
        self.company_name = company_name
        self.email = email
        
lead1 = Lead("ACME Corp", "contact@acme.com")
print(lead1.company_name)
print(lead1.email) """

#Returns:ACME Corp + contact@acme.com

class Lead:
    def __init__(self, company_name, email):
        self.company_name = company_name
        self.email = email
    
    def display_info(self):
        print(f"Company: {self.company_name}")
        print(f"Email: {self.email}")


lead1 = Lead("ACME Corp", "contact@acme.com")
lead1.display_info()

#Returns:ACME Corp + contact@acme.com


lead2 = Lead("PGCMC", "contact@pgcmc.org")
lead2.display_info()

# Returns: PGCMC + contact@pgcmc.org