import time

def read_csv_rows(filename):
    """
    Generator that yields one row at a time as a dictionary
    
    For test_data.csv, should yield:
    {'name': 'Alice', 'age': '30', 'city: 'NYC'}
    {'name': 'Bob', 'age': '25', 'city: 'SF'}
    {'name': 'Carol', 'age': '35', 'city: 'LA'}
    """
    
    with open(filename) as f:
        # first line is headers
        header = f.readline().strip().split(',')
        
        # yield each data row as a a dict
        for line in f:
            values = line.strip().split(',')
            # create dict: {'name': 'Alice', 'age': '30', 'city: 'NYC', ...}
            
            
            row_dict = {}
            for key, value in zip(header, values):
                row_dict[key] = value
            yield row_dict
            

    
    
    
def filter_rows(rows, key, value):
    """
    Generator that filters rows where row[key] == value
    
    Example: filter_rows(read_csv_rows('test.csv'), 'city', 'NYC')
    Should yield only rows where city == 'NYC'
    
    Args:
        rows: A generator/iterable of dictionaries
        key: The dictionary key to check (e.g., 'city')
        value: The value to match (e.g., 'NYC')
    
    Yields:
        Dictionaries where row[key] == value
    """
    for row in rows:
        # YOUR CODE: 
        # If row[key] equals value, yield the row
        if row[key] == value:
            yield row    
        



def transform_age_to_int(rows):
    """
    Generator that converts age from string to int
    
    Input row:  {'name': 'Alice', 'age': '30', 'city': 'NYC'}
    Output row: {'name': 'Alice', 'age': 30, 'city': 'NYC'}
                                        ^
                                        int, not string
    """
    for row in rows:
        # YOUR CODE:
        # Convert row['age'] from string to int
        # Yield the modified row
        row['age'] = int(row['age'])
        yield row



start = time.time()
count = 0

# Your generator should handle this efficiently
for row in read_csv_rows('large_test.csv'):
    count += 1
    if count % 100000 == 0:  # Progress update every 100k rows
        print(f"Processed {count:,} rows")

end = time.time()
print(f"\nTotal: {count:,} rows in {end - start:.2f} seconds")


print("\nFiltering for people in City42...")
start = time.time()

rows = read_csv_rows('large_test.csv')
city42 = filter_rows(rows, 'city', 'City42')
transformed = transform_age_to_int(city42)

count = 0
for row in transformed:
    count += 1

end = time.time()
print(f"Found {count:,} people in City42 in {end - start:.2f} seconds")