class FileHandler:
    def __init__(self, filename, mode):
        self.filename = filename
        self.mode = mode
        self.file = None    # how are we initializing a file attrib that we didnt pass into __init__
        
    def __enter__(self):
        """Called when entering 'with' block"""

        print(f"Opening {self.filename}")
        self.file = open(self.filename, self.mode)
        
        return self.file
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Called when exiting 'with' block, even if error occcured"""

        print(f"Closing {self.filename}")
        if self.file:
            self.file.close()
            
        return False
    
with FileHandler('test.txt', 'w') as f:
    f.write('Hello World')
    
# what is f here? what is w? where are __enter__ and __exit__ being called


with FileHandler('test_data.csv', 'w') as csv:
    csv.write('name,age,city\n')
    csv.write('Alice,30,NYC\n')
    csv.write('Bob,25,SF\n')
    csv.write('Carol,35,LA\n')
    

class CSVFileHandler:
    def __init__(self, filename):
        self.filename = filename
        self.file = None
        
    def __enter__(self):
       self.file = open(self.filename) 
       
       return self.file
   
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.file:
            self.file.close()


with CSVFileHandler('test_data.csv') as f:
    for line in f:
        print(line.strip())
        
""" Returns: 
name, age, city
Alice, 30, NYC
Bob, 25, SF
Carol, 35, LA """