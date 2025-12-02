class Counter:
    def __init__(self, start_value):
        self.count = start_value
        
    def increment(self):
        self.count += 1
        
    def get_count(self):
        return self.count
    
    
counter1 = Counter(0)
counter2 = Counter(100)

counter1.increment()
counter1.increment()
counter2.increment()

print(counter1.get_count())
print(counter2.get_count())

""" 
Question for you: Why do counter1 and counter2 have different counts even though they're the same class?

Answer: Self is doing something that each time a counter is initialized it is its own instance seperate from the other one
"""