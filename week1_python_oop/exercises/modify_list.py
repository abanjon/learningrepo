def modify_list(my_list):
    my_list.append(999)
    return my_list

original = [1, 2, 3]
result = modify_list(original)
print(original)  # What prints?
print(result)    # What prints?


""" 
Both print [1, 2, 3, 999]. Why? 
Lists in Python are passed by reference.
When you modify my_list inside the function, you're modifying the SAME object that original points to. 
Also, .append() adds to the END, not beginning. 
"""